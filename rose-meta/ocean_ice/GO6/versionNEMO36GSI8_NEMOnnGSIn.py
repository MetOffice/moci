import rose.upgrade
import re
import sys


class UpgradeError(Exception):

      """Exception created when an upgrade fails."""

      def __init__(self, msg):
          self.msg = msg

      def __repr__(self):
          sys.tracebacklimit = 0
          return self.msg

      __str__ = __repr__


class go6_cice_nprocs(rose.upgrade.MacroUpgrade):

    """Upgrade macro for setting default value of cice nprocs"""

    BEFORE_TAG = "nemo36_gsi8"
    AFTER_TAG = "go6_cice_nprocs"

    def upgrade(self, config, meta_config=None):
        """Upgrade a GO6 runtime app configuration."""
        # Input your macro commands here

        self.change_setting_value(config, ["namelist:domain_nml", "nprocs"],
                                  "'set_by_system'")
        return config, self.reports


class go6_gsi8_v2(rose.upgrade.MacroUpgrade):

    """Upgrade macro to move to nemo36_gsi8_v2 (with extra option for freshwater input from ice shelves)"""

    BEFORE_TAG = "go6_cice_nprocs"
    AFTER_TAG = "nemo36_gsi8_v2"

    def upgrade(self, config, meta_config=None):
        """Upgrade a GO6 runtime app configuration."""
        # Input your macro commands here

        # The following is only pertinent to coupled models. Make it conditional! 
        try:
           ln_coupled_iceshelf_fluxes = self.get_setting_value(config, 
                                        ["namelist:namsbc_cpl", "ln_coupled_iceshelf_fluxes"])

           if ln_coupled_iceshelf_fluxes.lower() == ".true.":
               self.add_setting(config,
                               ["namelist:namsbc_cpl", "nn_coupled_iceshelf_fluxes"],"1")
           else:
              self.add_setting(config,
                               ["namelist:namsbc_cpl", "nn_coupled_iceshelf_fluxes"],"0")
 
           self.remove_setting(config, ["namelist:namsbc_cpl", "ln_coupled_iceshelf_fluxes"])

           # Need to add these to the configuration. Only used if nn_coupled_iceshelf_fluxes is changed
           # to 2 in which case we hope the user will think to set these values to something sensible. 
           self.add_setting(config, ["namelist:namsbc_cpl", "rn_greenland_total_fw_flux"],"0.0")
           self.add_setting(config, ["namelist:namsbc_cpl", "rn_antarctica_total_fw_flux"],"0.0")
 
        except:
           print("Ice shelf coupling not relevant. No action necessary.")


        # Get rid of any redundant ancient variables in namtra_dmp.
	# These have never existed in any form in the GO6 package branch
	# but appear to be present in some suite interfaces!  
        try:
           self.remove_setting(config,["namelist:namtra_dmp", "nn_file"])
           self.remove_setting(config,["namelist:namtra_dmp", "nn_hdmp"])
           self.remove_setting(config,["namelist:namtra_dmp", "rn_bot"])
           self.remove_setting(config,["namelist:namtra_dmp", "rn_dep"])
           self.remove_setting(config,["namelist:namtra_dmp", "rn_surf"])
        except:
           print("No namtra_dmp variables need removing.")	   
	   

        self.change_setting_value(config, ["namelist:domain_nml", "nprocs"],
                                  "'set_by_system'")
        return config, self.reports

class go6_gsi8_v3(rose.upgrade.MacroUpgrade):

    """Upgrade macro to move from go6_gsi8_v2 to nemo36_gsi8_v3 """

    BEFORE_TAG = "nemo36_gsi8_v2"
    AFTER_TAG = "nemo36_gsi8_v3"

    def upgrade(self, config, meta_config=None):
        """Upgrade NEMO runtime app, if appropriate""" 
	
	# Many existing NEMO suites seem to pointlessly cary around a reference
	# to namelist namobc which has not been present in the code since 2013!
	# Remove it, if it's present. 

        # Extract the list of NEMO namelists
        nl_list = self.get_setting_value(config, ["file:namelist_cfg", "source"]) 
      
        # See if the offending redundant namelist is present.
        if re.search(r'namelist:namobc', nl_list):
	   # Remove the namelist and its variables
           self.remove_setting(config,["namelist:namobc"])
	   # Remove the entry from the list of namelists
           self.change_setting_value(config,["file:namelist_cfg","source"],
	                nl_list.replace("namelist:namobc ",""))
            
        else:
           print("No NEMO component upgrades necessary.")
            
        """Upgrade CICE runtime app configuration, if appropriate."""

        # Check to see if CICE is active. We do this based on nn_ice
	# in the NEMO SBC settings. A value of 4 indicates CICE. 
        # We do nothing for any non CICE options. 	
        nn_ice = self.get_setting_value(config, 
                                        ["namelist:namsbc", "nn_ice"])

        if (nn_ice == '4'):
           print("Checking CICE component for upgrades")

           # Set up a generic string to populate fields which are automatically set by 
	   # the drivers, etc at run time. 
           system_set = "'set_by_system'"

           days_per_year = self.get_setting_value(config, 
                                        ["namelist:setup_nml", "days_per_year"])
           if not days_per_year.isdigit():
              self.change_setting_value(config, 
	                ["namelist:setup_nml", "days_per_year"], system_set)
	    
           # npt can only be set by the system
           self.change_setting_value(config, 
	                ["namelist:setup_nml", "npt"], system_set)
	        
           # Pointer file can only be set by the system
           self.change_setting_value(config, 
	                ["namelist:setup_nml", "pointer_file"], system_set)
	    
           # Restart file can only be set by the system
           self.change_setting_value(config, 
	                ["namelist:setup_nml", "restart_file"], system_set)
	    
           # Leap year control can only be set by the system
           self.change_setting_value(config, 
	                ["namelist:setup_nml", "use_leap_years"], system_set)

           # Examine history_file 
           history_file = self.get_setting_value(config, 
                                        ["namelist:setup_nml", "history_file"])
           if "set_by" in history_file:
              # The set_by_ value could take any one of a number of 
	      # forms. Here we just standardise its value. 
              self.change_setting_value(config, 
	                ["namelist:setup_nml", "history_file"], system_set)

           # Initial year control can only be set by the system
           self.change_setting_value(config, 
	                ["namelist:setup_nml", "year_init"], system_set)

           # ice_ic can take one of three values. If it's
	   # not set to default or none, then allow it to 
	   # be automatically set. 
           ice_ic = self.get_setting_value(config, 
                                        ["namelist:setup_nml", "ice_ic"])
           if not (ice_ic == 'default') and not (ice_ic == 'none'):
           # The set_by_ value could take any one of three of 
	   # forms. Here we just standardise its value if not already 
	   # set to 'none' or 'default'.         
             self.change_setting_value(config, 
	                ["namelist:setup_nml", "ice_ic"], system_set)
	    
           # Examine restart (this is not the same as restart_file!)
           self.change_setting_value(config, 
	                ["namelist:setup_nml", "restart"], system_set)

           # Examine incond_file 
           incond_file = self.get_setting_value(config, 
                                        ["namelist:setup_nml", "incond_file"])
           if "set_by" in incond_file:
              # The set_by_ value could take any one of a number of 
	      # forms. Here we just standardise its value. 
              self.change_setting_value(config, 
	                ["namelist:setup_nml", "incond_file"], system_set)

           diag_set = "'ice_diag.d'"
           # Ensure diag_file is set to the only value allowed 
           self.change_setting_value(config, 
	                ["namelist:setup_nml", "diag_file"], diag_set)

 
           # istep0 can be set to 0 since the drivers will set this to an 
	   # appropriate value at run time. But the point here is that 
	   # some suites may have this as a string! We need 
	   # an integer. 
           self.change_setting_value(config, 
	                ["namelist:setup_nml", "istep0"], "0")

        else:
           print("No CICE component upgrades necessary.")


        return config, self.reports

class go6_gsi8_v4(rose.upgrade.MacroUpgrade):

    """Upgrade macro to move from go6_gsi8_3 to nemo36_gsi8_v4 """

    BEFORE_TAG = "nemo36_gsi8_v3"
    AFTER_TAG = "nemo36_gsi8_v4"

    def upgrade(self, config, meta_config=None):
        """Upgrade a GO6 runtime app configuration."""
        # Input your macro commands here
        #sn_cfctl%l_runstat
        try:
           l_runstat = self.get_setting_value(config,
                                        ["namelist:namctl", "sn_cfctl%l_runstat"])
           if l_runstat:
              print("sn_cfctl%l_runstat is in namelist; No action necessary.")
           else:
              print("Set sn_cfctl%l_runstat in namctl")
              self.add_setting(config,
                               ["namelist:namctl", "sn_cfctl%l_runstat"],".true.")
        except:
           print("Problem with sn_cfctl%l_runstat")

        #sn_cfctl%l_trcstat
        try:
           l_trcstat = self.get_setting_value(config,
                                        ["namelist:namctl", "sn_cfctl%l_trcstat"])
           if l_trcstat:
              print("sn_cfctl%l_trcstat is in namelist; No action necessary.")
           else:
              print("Set sn_cfctl%l_trcstat in namctl")
              self.add_setting(config,
                               ["namelist:namctl", "sn_cfctl%l_trcstat"],".true.")
        except: 
           print("Problem with sn_cfctl%l_trcstat")

        #sn_cfctl%ptimincr
        try:
           ptimincr = self.get_setting_value(config,
                                        ["namelist:namctl", "sn_cfctl%ptimincr"])
           if ptimincr:
              print("sn_cfctl%ptimincr is in namelist; No action necessary.")
           else:
              print("Set sn_cfctl%ptimincr in namctl")
              self.add_setting(config,
                               ["namelist:namctl", "sn_cfctl%ptimincr"],"1")
        except:
           print("Problem with sn_cfctl%ptimincr")

        #ln_flush
        try:
           ln_flush = self.get_setting_value(config,
                                        ["namelist:namctl", "ln_flush"])
           if ln_flush:
              print("ln_flush is in namelist; No action necessary.")
           else:
              print("Set ln_flush in namctl")
              self.add_setting(config,
                               ["namelist:namctl", "ln_flush"],".false.")
        except:
           print("Problem with ln_flush")

        return config, self.reports

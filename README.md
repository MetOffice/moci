# moci - Met Office Coupling Infrastructure

The Met Office global coupled models (GC) couple together the ​
[UM](https://github.com/MetOffice/um) and [​NEMO](https://www.nemo-ocean.eu/) in
order to create an atmosphere-ocean-ice-land modelling system of the physical
climate model. Moci is also used in the NGMS infrastructure, using
[LFRic](https://github.com/MetOffice/lfric_apps) as the atmosphere model.

The Met Office Coupling Infrastructure (MOCI) is a repository of codes that,
together with ​Rose suites, form the superstructure controlling the execution of
Met Office global coupled models components.

## Contributing Guidelines

Welcome!

The following links are here to help set clear expectations for everyone
contributing to this project. By working together under a shared understanding,
we can continuously improve the project while creating a friendly, inclusive
space for all contributors.

### Contributors Licence Agreement

Please see the
[Momentum Contributors Licence Agreement](https://github.com/MetOffice/Momentum/blob/main/CLA.md)

Agreement of the CLA can be shown by adding yourself to the CONTRIBUTORS.md file
alongside this one, and is a requirement for contributing to this project.

### Code of Conduct

Please be aware of and follow the
[Momentum Code of Coduct](https://github.com/MetOffice/Momentum/blob/main/docs/CODE_OF_CONDUCT.md)

### Working Practices

This project is managed as part of the Simulation Systems group of repositories.

Please follow the Simulation Systems
[Working Practices.](https://metoffice.github.io/simulation-systems/index.html)

Questions are encouraged in the Simulation Systems
[Discussions.](https://github.com/MetOffice/simulation-systems/discussions)

Please be aware of and follow the Simulation Systems
[AI Policy.](https://metoffice.github.io/simulation-systems/FurtherDetails/ai.html)

#### Testing

MOCI rose-stem provides testing for the Coupled_Drivers and Postprocessing applications plus Utilities unittests.
`cylc vip -z group=<group> -n <run name> <path to rose-stem dir>

Available test groups:
`all`       Runs all available tasks
`tests`     Runs all unit tests covering MOCI code
`postproc`  Runs all Postprocessing application tasks
`drivers`   Runs all Coupled_Drivers related tasks.
            Drivers run tasks currently only available on Met Office internal machines.
            `drivers_non_run` tests are available on other platforms



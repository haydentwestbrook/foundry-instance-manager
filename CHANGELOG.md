# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## Unrealeased

<small>[Compare with latest](https://github.com/haydentwestbrook/foundry-instance-manager/compare/72a22c57cedcb0e420bd26e74e575b6adc3bcea3...HEAD)</small>

### Added
- Add version management and ci/cd pipeline: - add bump2version for semantic versioning - create version bump script - add github actions workflows for ci and releases - configure pypi publishing ([af605ef](https://github.com/haydentwestbrook/foundry-instance-manager/commit/af605ef9a1a726025a1db327e26b9e19228b8605) by Hayden Westbrook).
- Adding ability to create instances from config file ([f3617e7](https://github.com/haydentwestbrook/foundry-instance-manager/commit/f3617e772f0600ae330c80a8cccd0da1f41411e1) by Hayden Westbrook).

### Fixed
- Fix: add setuptools dependency for git-changelog ([3c6e095](https://github.com/haydentwestbrook/foundry-instance-manager/commit/3c6e095dc048b9d3658a5e673f2e4efcfe02da9f) by Hayden Westbrook).
- Fix: move build step to release workflow and use poetry consistently ([4d0372a](https://github.com/haydentwestbrook/foundry-instance-manager/commit/4d0372a5b0ea06a944f9151f73c5daa0e959057a) by Hayden Westbrook).
- Fix: switch to poetry for dependency management and building ([a305b58](https://github.com/haydentwestbrook/foundry-instance-manager/commit/a305b5872ec7ec44cec9f3aa2c555bb89bca3b14) by Hayden Westbrook).
- Fix: update ci workflow with build dependencies and build step ([d41e0da](https://github.com/haydentwestbrook/foundry-instance-manager/commit/d41e0da6f24644721271a15051f794fd0d511a3e) by Hayden Westbrook).
- Fix: add build package to ci dependencies ([75c5e4e](https://github.com/haydentwestbrook/foundry-instance-manager/commit/75c5e4e87526178f766a178b07ea191c74b351df) by Hayden Westbrook).
- Fix: install git-changelog in release workflow ([c8dd62e](https://github.com/haydentwestbrook/foundry-instance-manager/commit/c8dd62ef7447cbfd545f50cecb143dd2737fe891) by Hayden Westbrook).
- Fix: correct package name to foundry_instance_manager ([c27c7eb](https://github.com/haydentwestbrook/foundry-instance-manager/commit/c27c7eb931d6ecc6a2555b3f07674c5fc0df5e22) by Hayden Westbrook).
- Fix: update package name and structure in pyproject.toml ([2deba02](https://github.com/haydentwestbrook/foundry-instance-manager/commit/2deba022caa5365e7a52c470c900aa348bb497c3) by Hayden Westbrook).
- Fix: resolve flake8 issues across multiple files ([a1766f6](https://github.com/haydentwestbrook/foundry-instance-manager/commit/a1766f602cb2887b90578428093272891e427c7d) by Hayden Westbrook).
- Fix: correct port mapping and error handling in docker manager ([42fcc13](https://github.com/haydentwestbrook/foundry-instance-manager/commit/42fcc13e77ba922cf323200ec48e3ff9bcd7b7b5) by Hayden Westbrook).
- Fix: improve type checking and code quality ([7fd7fe8](https://github.com/haydentwestbrook/foundry-instance-manager/commit/7fd7fe820663cfc975f74920f11a961c3ea615ca) by Hayden Westbrook).
- Fix: improve docker manager error handling and port mapping ([0f98e31](https://github.com/haydentwestbrook/foundry-instance-manager/commit/0f98e313b20a772ef20d104bf507191080996b83) by Hayden Westbrook).
- Fixing build and adding tsconfig ([432d55d](https://github.com/haydentwestbrook/foundry-instance-manager/commit/432d55d5bd70474225a621aea27f5e9cd477a0a0) by Hayden).

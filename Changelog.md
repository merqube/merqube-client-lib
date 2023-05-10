# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.5] - 2023-05-10
- add logging statement to debug cache issues

## [0.5.4] - 2023-05-10
- Improve logging message (it wasn't using `urljoin`)

## [0.5.3] - 2023-05-08
- standardize/consistent naming (`user_session` vs `session`)
- support arbitrary args in mock class call

## [0.5.2] - 2023-05-06
- allow positional on public methods

## [0.5.1] - 2023-05-05
- Fix bug; artificial restriction on secnames or ids; it is currently legal (whether it should be, different question..) to use neither, which results in the metric across all securities

## [0.5.0] - 2023-05-04
- Add `get_security_metrics`, the main call for retrieving metrics from Merqubes security api

## [0.4.0] - 2023-05-03
- First batch of secapi client code
- secapi mocker

## [0.3.0] - 2023-05-02
- add logging lib

## [0.2.3] - 2023-05-02
- Add missing py.typed file, and PYPI description

## [0.2.2] - 2023-05-02
- Relax more dependency constraints (pandas, numpy)

## [0.2.1] - 2023-05-02
- Do not restrict 3.10

## [0.2.0] - 2023-05-02
- Release base session

## [0.1.0] - 2023-05-01
- Repo creation

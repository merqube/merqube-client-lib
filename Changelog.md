# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.13.1] - 2023-06-19
- add merge job

## [0.13.0] - 2023-06-12
- Add support for updating target portfolios of an existing basket index
- Restructure to support corax on multi-baskets
- support passing in the pydantic object or dict in client lib functions
- add `MERQ_API_KEY` in circle-ci secrets that allows int tests. Add said int tests
- add `start_date` and `end_date` functionality into getting target portfolios

## [0.12.1] - 2023-06-09
- some index specs use `calendar` while others use `holiday_spec` - set both.

## [0.12.0] - 2023-06-08
- Use ENV for APIKey, so configs are shareable.
- Allow users to specify their own TR indices

## [0.11.0] - 2023-06-05
- Reorganize to have a single click script before we have a ton of them
- add decrement index template
- add holiday spec

## [0.10.0] - 2023-06-01
- Add client and template for creating multiple stock equity baskets (no corax)
- Add client and template for creating a single stock total return index with corax

## [0.9.0] - 2023-05-25
- Make base classes private now that nothing is importing them directly.

## [0.8.2] - 2023-05-24
- copy the headers object if the client passes it in

## [0.8.1] - 2023-05-24
- add the failed request id into the `APIError` object, and logging that occurs on failure
- Move request id header generation into `MerqubeAPISession` instead of the `_Base`

## [0.8.0] - 2023-05-16
- Implement NotImplemented returns/metrics methods for single index
- add more power to the secapi mocker; can now also mock session level methods
- add intraday support
- kill `get_client` from secapi and move module
- add logging to the secapi mocker

## [0.7.0] - 2023-05-15
- add class for managing a single index
- more tests

## [0.6.0] - 2023-05-11
- add start of Index API Client
- add unified client that mixins both to produce one total-api client
- repo re-organization

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

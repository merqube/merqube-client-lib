# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.16.4] - 2023-07-14
- move json parsing into cli script, so we can programatically use the underlying functions to create indices in a loop
- update to latest types

## [0.16.3] - 2023-07-13
- allow specifying a default request id prefix, so all requests made from the same "project" can be tracked easily
- circleci improvements

## [0.16.2] - 2023-07-05
- bugfix; for index templates, `base_value` wasn't propogating correctly into `base_val`

## [0.16.1] - 2023-06-29
- allow (but not require) pandas2
- fix issue with timezone on logger tests

## [0.16.0] - 2023-06-28
- support manifest locking/unlocking
- some minor breaking changes for index clients (not 1.0.0 yet!) RE positionl vs kwargs - index client functions now accept name or id
- add lots more testing

## [0.15.2] - 2023-06-23
- README update. Need to enhance the circleci logic so we dont have merge job failures for readme updates that dont bump the version

## [0.15.1] - 2023-06-21
- fix typo

## [0.15.0] - 2023-06-20
- switch to pydantic for validation and client models; eliminate json checking
- add some extra example docs for equity baskets

## [0.14.0] - 2023-06-16
- add support for multiple equity baskets with corax
- add walkthrough for multiple equity baskets

## [0.13.3] - 2023-06-19
- finish merge job

## [0.13.2] - 2023-06-19
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

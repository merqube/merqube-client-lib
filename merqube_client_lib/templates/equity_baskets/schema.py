from __future__ import annotations

import json
from datetime import date
from enum import Enum
from typing import Any, cast

import pytz
from pydantic import (
    BaseModel,
    Extra,
    Field,
    PrivateAttr,
    StrictBool,
    StrictStr,
    validator,
)
from pydantic.types import PositiveFloat, T

from merqube_client_lib.pydantic_types import HolidayCalendarSpec


class HolidayCalendar(BaseModel):
    class Config:
        extra = Extra.forbid

    mics: list[StrictStr] = Field(default_factory=list)
    swaps_monitor_codes: list[StrictStr] = Field(default_factory=list)


class DecrementFeeType(Enum):
    fixed = "fixed"
    percentage_pre = "percentage_pre"
    percentage_post = "percentage_post"


class ClientIndexConfigBase(BaseModel):
    class Config:
        extra = Extra.forbid

    base_date: date = Field(
        description="set to a business day before the intended start date for the real-time calcs", example="2000-01-01"
    )

    # not all indices have this eg a single stock tr indices is just shares * price on the base_date
    base_value: PositiveFloat | None = Field(
        None, description="set to the value of the index on the base_date", example=1000.0
    )

    bbg_ticker: StrictStr | None = Field(
        None,
        description="due to the limitations of the Bloomberg ticker creation process (no API), this must be a pre-created ticker. You can email MerQube a list of tickers to create on your behalf at support@merqube.com. Then, you provide those as input to these indices",
        example="MY_TICKER",
    )

    currency: StrictStr = Field("USD", description="set to the currency of the index", example="USD")

    description: StrictStr = Field(
        description="set to the description of the index, which will show on merqube.com",
        example="My Index Description",
    )

    email_list: list[StrictStr] = Field(
        default_factory=list,
        description="list of emails to send daily dissemination reports, and the initial backtest reports, to; if not specified, no emails will be sent",
        example=["bob@mycompany.com", "alice@mycompany.com"],
    )

    is_intraday: StrictBool = Field(False, description="set to True if the index is intraday", example=False)

    name: StrictStr = Field(
        description="set to the name of the index. Commonly people use the ticker as the name, but that is not necessary. Must be globally unique - you will get a 409 if this index name is taken ",
        example="My Index",
    )

    namespace: StrictStr = Field(description="set to the namespace of the index", example="mycompany")

    run_hour: int = Field(description="set to the hour of day to run the index in the index's timezone", example=16)

    run_minute: int = Field(description="set to the minute of the hour to run the index ", example=0)

    timezone: StrictStr = Field("US/Eastern", description="set to the timezone of the index", example="US/Eastern")

    title: StrictStr = Field(
        description="set to the title of the index that shows up on merqube.com", example="My Index Title"
    )

    # set by the client lib
    _holiday_spec_: HolidayCalendarSpec | None = PrivateAttr(None)

    @classmethod
    def get_example(cls) -> dict[str, Any]:
        """
                Construct an example from the class schema
                adapted from https://github.com/pydantic/pydantic/discussions/4558
        __holiday_spec__"""
        d = {}
        for field_name, model_field in cls.__fields__.items():
            if "example" in model_field.field_info.extra:
                d[field_name] = model_field.field_info.extra["example"]

        instance = cls(**d)
        return cast(dict[str, Any], json.loads(instance.json()))

    @validator("timezone")
    def is_valid_tz(cls: T, v: str) -> str:  # pylint: disable=no-self-argument
        if v not in pytz.all_timezones:
            raise ValueError(f"Invalid timezone string: {v}")
        return v

    @validator("run_hour")
    def is_valid_hour(cls: T, v: int) -> int:  # pylint: disable=no-self-argument
        if v < 0 or v > 23:
            raise ValueError(f"Invalid timezone string: {v}")
        return v

    @validator("run_minute")
    def is_valid_minute(cls: T, v: int) -> int:  # pylint: disable=no-self-argument
        if v < 0 or v > 59:
            raise ValueError(f"Invalid timezone string: {v}")
        return v


class _ClientIndexWithCalendarBase(BaseModel):
    class Config:
        extra = Extra.forbid

    holiday_calendar: HolidayCalendar | None = Field(
        None,
        description="set to the holiday calendar for the index, default is M_F (weekdays)",
        example={"mics": ["XNYS"]},
    )


class CorporateActions(BaseModel):
    reinvest_dividends: StrictBool = True


class ReinvestmentType(Enum):
    AT_OPEN = "AT_OPEN"  # reinvest at previous day's prices
    AT_CLOSE = "AT_CLOSE"  # reinvest at the end of the effective date


reinvestment_mapping = {
    ReinvestmentType.AT_OPEN: "PREV_DAY",
    ReinvestmentType.AT_CLOSE: "EFF_DAY",
}


class ClientSSTRConfig(ClientIndexConfigBase, _ClientIndexWithCalendarBase):
    """
    Single stock total return index
    """

    class Config:
        extra = Extra.forbid

    ric: StrictStr = Field(description="set to the RIC of the underlying equity", example="LMVH.PA")

    reinvestment_type: ReinvestmentType = Field(
        default=ReinvestmentType.AT_OPEN, description="set to the type of reinvestment to apply", example="AT_OPEN"
    )


class ClientDecrementConfig(ClientIndexConfigBase):
    """
    Decrement index on top of an SSTR
    Calendar automatically set to that of the underlying
    """

    class Config:
        extra = Extra.forbid

    fee_value: float = Field(
        description="set to the value of the fee to apply. For fixed, this is bps, for percentage_pre/post this is given as a percentage",
        example=0.05,
    )

    fee_type: DecrementFeeType = Field(description="set to the type of fee to apply", example="fixed")

    day_count_convention: StrictStr = Field(
        description="must either adapt to a fixed number of days in a year e.g. 'f360' or to Actual ISDA convention, i.e. 'actual'",
        example="f360",
    )

    ric: StrictStr = Field(description="set to the RIC of the underlying SSTR", example="LMVH.PA")

    start_date: date | None = Field(
        None,
        description="set to the start date of the index if it is to differ from base_date. If this is specified, it must be before base_date. In this case the base_date, base_value is used as a fixed intercept, with the index level starting from start_date and passing through that intercept",
        example="2000-01-01",
    )


class ClientMultiEquityBasketConfig(ClientIndexConfigBase, _ClientIndexWithCalendarBase):
    """
    Equity Basket
    """

    class Config:
        extra = Extra.forbid

    constituents_csv_path: StrictStr = Field(
        description="set to the path to the constituents csv. There is an example in this directory",
        example="/path/to/my.csv",
    )

    corporate_actions: CorporateActions = Field(
        default_factory=CorporateActions,
        description="how to handle corporate actions",
        example={"reinvest_dividends": True},
    )

    level_overrides_csv_path: StrictStr | None = Field(
        None,
        description="path to a csv file like the level_overrides.csv in this directory, if there are specific dates that need to be overridden",
    )

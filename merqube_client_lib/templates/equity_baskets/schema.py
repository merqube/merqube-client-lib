from __future__ import annotations

from datetime import date
from enum import Enum

import pytz
from pydantic import BaseModel, Extra, Field, StrictBool, StrictStr, validator
from pydantic.types import T

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

    base_date: date
    # not all indices have this eg a single stock tr indices is just shares * price on the base_date
    base_value: int | float | None = None
    bbg_ticker: StrictStr | None = None
    currency: StrictStr = "USD"
    description: StrictStr
    email_list: list[StrictStr] = Field(default_factory=list)
    holiday_calendar: HolidayCalendar | None
    is_intraday: StrictBool = False
    name: StrictStr
    namespace: StrictStr
    run_hour: int
    run_minute: int
    timezone: StrictStr = "US/Eastern"
    title: StrictStr

    # set by the client lib
    holiday_spec: HolidayCalendarSpec | None = None

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


class CorporateActions(BaseModel):
    reinvest_dividends: StrictBool = True


class ClientSSTRConfig(ClientIndexConfigBase):
    """
    Single stock total return index
    """

    class Config:
        extra = Extra.forbid

    underlying_ric: StrictStr


class ClientDecrementConfig(ClientIndexConfigBase):
    """
    Decrement index on top of an SSTR
    """

    class Config:
        extra = Extra.forbid

    underlying_index_name: StrictStr
    fee_value: float
    fee_type: DecrementFeeType
    day_count_convention: StrictStr
    client_owned_underlying: bool = True


class ClientMultiEquityBasketConfig(ClientIndexConfigBase):
    """
    Equity Basket
    """

    class Config:
        extra = Extra.forbid

    constituents_csv_path: StrictStr
    corporate_actions: CorporateActions = Field(default_factory=CorporateActions)
    level_overrides_csv_path: StrictStr | None = None

"""Register overtime command for the Telegram bot."""

from apps.telegram.bot.commands import Command
from apps.telegram.bot.steps import (
    CombineDateTime,
    Confirm,
    InsertTimesheetItems,
    SelectDate,
    SelectItemType,
    SelectProject,
    Step,
    WaitForDescription,
    WaitForTime,
)


class RegisterOvertime(Command):
    """Represent the register overtime command."""

    command = "/registerovertime"
    description = "Register overtime for a specific day on a specific project."

    @property
    def steps(self) -> list[Step]:
        """Return the steps of the command."""
        return [
            SelectProject(self),
            SelectDate(self, key="start_date", steps_back=1),
            WaitForTime(self, key="start_time", date_key="start_date"),
            CombineDateTime(self, date_key="start_date", time_key="start_time"),
            SelectDate(self, key="end_date", initial_date_key="start_time", unique_id="SelectEndDate", steps_back=3),
            WaitForTime(self, key="end_time", date_key="end_date", unique_id="WaitForEndTime"),
            CombineDateTime(self, date_key="end_date", time_key="end_time", unique_id="CombineEndDateTime"),
            WaitForDescription(self, steps_back=3),  # back to SelectEndDate
            SelectItemType(self, steps_back=1),
            Confirm(self, steps_back=1),
            InsertTimesheetItems(self),
        ]

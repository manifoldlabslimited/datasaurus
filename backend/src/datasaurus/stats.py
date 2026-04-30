"""Summary statistics computation and constraint checking."""

from typing import Self

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TargetStats(BaseModel):
    """Target summary statistics for a generated dataset."""

    model_config = ConfigDict(frozen=True)

    mean_x: float = Field(default=54.26, description="Target mean of x")
    mean_y: float = Field(default=47.83, description="Target mean of y")
    std_x: float = Field(default=16.76, gt=0, description="Target std dev of x")
    std_y: float = Field(default=26.93, gt=0, description="Target std dev of y")
    correlation: float = Field(default=-0.06, ge=-1.0, le=1.0, description="Target Pearson correlation")
    tolerance: float = Field(default=0.01, gt=0, description="Max allowed deviation from each target stat")

    @model_validator(mode="after")
    def check_tolerance_sensible(self) -> Self:
        if self.tolerance > 1.0:
            raise ValueError("Tolerance > 1.0 is too loose to be meaningful")
        return self


def compute_stats(df: pd.DataFrame) -> pd.Series:
    """Compute the five summary statistics for a DataFrame with x and y columns."""
    return pd.Series({
        "mean_x": df["x"].mean(),
        "mean_y": df["y"].mean(),
        "std_x": df["x"].std(),
        "std_y": df["y"].std(),
        "correlation": df["x"].corr(df["y"]),
    })


def stats_are_valid(x: np.ndarray, y: np.ndarray, target: TargetStats) -> bool:
    """Return True if all statistics are within tolerance of target.

    Uses raw numpy to stay fast — called 200k times per SA run.
    """
    tol = target.tolerance
    return (
        abs(float(np.mean(x)) - target.mean_x) <= tol
        and abs(float(np.mean(y)) - target.mean_y) <= tol
        and abs(float(np.std(x, ddof=1)) - target.std_x) <= tol
        and abs(float(np.std(y, ddof=1)) - target.std_y) <= tol
        and abs(float(np.corrcoef(x, y)[0, 1]) - target.correlation) <= tol
    )

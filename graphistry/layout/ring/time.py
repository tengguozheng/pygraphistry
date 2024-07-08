from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union
import numpy as np
import pandas as pd
from functools import lru_cache
from graphistry.Plottable import Plottable


TimeUnit = Literal['s', 'm', 'h', 'D', 'W', 'M', 'Y', 'C']
"""Time unit for axis labels

- 's': seconds
- 'm': minutes
- 'h': hours
- 'D': days
- 'W': weeks
- 'M': months
- 'Y': years
- 'C': centuries

"""


@lru_cache
def unit_to_timedelta(unit: TimeUnit) -> np.timedelta64:
    map: Dict[TimeUnit, np.timedelta64] = {
        's': np.timedelta64(1, 's'),
        'm': np.timedelta64(60, 's'),
        'h': np.timedelta64(3600, 's'),
        'D': np.timedelta64(86400, 's'),
        'W': np.timedelta64(7 * 86400, 's'),
        'M': np.timedelta64(30, 'D'),  # Approximating a month
        'Y': np.timedelta64(365, 'D'),  # Approximating a year
        'C': np.timedelta64(100 * 365, 'D')  # Approximating a century
    }
    return map[unit]


def find_round_bin_width(
    duration: np.timedelta64, time_unit: Optional[TimeUnit] = None
) -> Tuple[TimeUnit, pd.DateOffset, np.timedelta64]:
    duration_seconds = np.timedelta64(duration, 's')
    units: List[Tuple[TimeUnit, pd.DateOffset, np.timedelta64]] = [
        ('s', pd.DateOffset(seconds=1), np.timedelta64(1, 's')),
        ('m', pd.DateOffset(minutes=1), np.timedelta64(60, 's')),
        ('h', pd.DateOffset(hours=1), np.timedelta64(3600, 's')),
        ('D', pd.DateOffset(days=1), np.timedelta64(86400, 's')),
        ('W', pd.DateOffset(weeks=1), np.timedelta64(7 * 86400, 's')),
        ('M', pd.DateOffset(months=1), np.timedelta64(31, 'D')),  # Approximating a month
        ('Y', pd.DateOffset(years=1), np.timedelta64(365, 'D')),  # Approximating a year
        ('C', pd.DateOffset(years=100), np.timedelta64(100 * 365, 'D'))  # Approximating a century
    ]

    if time_unit is not None:
        (unit, date_offset, td_unit) = [(x, y, z) for (x, y, z) in units if x == time_unit][0]

    for unit, date_offset, td_unit in (
        units
        #if time_unit is None else
        #[(x, y, z) for (x, y, z) in units if x == time_unit]
    ):
        if duration_seconds <= td_unit:
            print('HIT unit', unit, 'td_unit', td_unit)
            return unit, date_offset, td_unit
        print('MISS unit', unit, 'td_unit', td_unit)
    return 'C', pd.DateOffset(years=100), np.timedelta64(100 * 365, 'D')  # Default to centuries if too large


def round_to_nearest(time: np.datetime64, unit: np.timedelta64) -> np.datetime64:

    # Convert the unit to nanoseconds
    unit_in_ns = unit.astype('timedelta64[ns]').astype('int64')
    
    # Convert time to nanoseconds since epoch
    time_in_ns = time.astype('datetime64[ns]').astype('int64')
    
    # Avoid rounding error issues
    adjustment = unit_in_ns // 2

    # Calculate the number of units since the epoch
    rounded_time_in_ns = ((time_in_ns + adjustment) // unit_in_ns) * unit_in_ns

    # Convert back to the original datetime64 format
    rounded_time = rounded_time_in_ns.astype('datetime64[ns]')

    return rounded_time


def pretty_print_time(time: np.datetime64, round_unit: TimeUnit) -> str:
    if round_unit == 's':
        return time.astype('datetime64[s]').astype(str)
    elif round_unit == 'm':
        return time.astype('datetime64[m]').astype(str)
    elif round_unit == 'h':
        return time.astype('datetime64[h]').astype(str)
    elif round_unit == 'D':
        return time.astype('datetime64[D]').astype(str)
    elif round_unit == 'W':
        return time.astype('datetime64[W]').astype(str)
    elif round_unit == 'M':
        return time.astype('datetime64[M]').astype(str)
    elif round_unit == 'Y':
        return time.astype('datetime64[Y]').astype(str)
    else:
        return str(time)

def time_stats(
    s: pd.Series,  # datetime64[ns]
    num_rings: Optional[int] = 20,
    time_start: Optional[np.datetime64] = None,
    time_end: Optional[np.datetime64] = None,
    time_unit: Optional[TimeUnit] = None
) -> Tuple[TimeUnit, np.timedelta64, pd.DateOffset, np.datetime64, np.datetime64, int]:

    if time_start is None:
        time_start = s.min().to_numpy()
    if time_end is None:
        time_end = s.max().to_numpy()

    assert isinstance(time_start, np.datetime64)
    assert isinstance(time_end, np.datetime64)
    print('time_start', time_start)
    print('time_end', time_end)
    print('dur', np.timedelta64((time_end - time_start), 'D'))

    if num_rings is None:
        if time_unit is not None:
            time_dur: np.timedelta64 = time_end - time_start
            unit_step = unit_to_timedelta(time_unit)
            rounded = (time_dur // unit_step).astype('int')
            num_rings = rounded + 1
        else:
            num_rings = 10 if len(s) > 1000 else 5
            print('target_bins', num_rings)
    
    step_dur_s = ((time_end - time_start) / num_rings)
    print('step_dur_s', step_dur_s)
    print('step_dur_s[D]', np.timedelta64(step_dur_s, 'D'))
    print('time_unit', time_unit)
    round_unit, rounded_set_offset, rounded_step_dur = find_round_bin_width(step_dur_s, time_unit=time_unit)
    print('rounded', step_dur_s, time_unit, '->', rounded_step_dur, round_unit, rounded_set_offset)

    time_start_rounded = round_to_nearest(time_start, rounded_step_dur)
    print('time_start_rounded', time_start, rounded_step_dur, '->', time_start_rounded)
    time_end_rounded = round_to_nearest(
        time_start_rounded + rounded_step_dur * num_rings,
        rounded_step_dur)

    return (
        round_unit,
        rounded_step_dur,
        rounded_set_offset,
        time_start_rounded,
        time_end_rounded,
        num_rings
    )

def gen_axis(
    num_rings: int,
    time_start: np.datetime64,
    step_dur: np.timedelta64,
    rounded_set_offset: pd.DateOffset,
    round_unit: TimeUnit,
    r_start: float,
    r_end: float,
    scalar: float,
    label: Optional[Callable[[np.datetime64, int, np.timedelta64], str]] = None,
    reverse: bool = False
) -> List[Dict]:
    
    def offset_time_to_r(
        offset: pd.DateOffset,
    ) -> float:
        #return (
        #    (time_start + offset).astype('int64') - time_start.astype('int64')
        #) * scalar + r_start
        time_start_timestamp = pd.Timestamp(time_start)
        
        # Add the DateOffset to the Timestamp
        print('adding', time_start, time_start_timestamp, offset)
        time_end_timestamp = time_start_timestamp + offset
        
        tf = time_end_timestamp.value - time_start_timestamp.value
        
        # Compute the result using the scalar and r_start
        out = tf * scalar + r_start

        if reverse:
            out = -out + (r_start + r_end)

        return out

    axis = [
      {
          "label": str(
              pretty_print_time(time_start + step_dur * step, round_unit)
          ) if label is None else label(
              time_start + step_dur * step, step, step_dur
          ),
          #"r": r_start + ((num_rings - step) if reverse else step) * step_r,
          "r": offset_time_to_r(rounded_set_offset * step),
          "internal": True
      }
      for step in range(0, num_rings + 1)
    ]
    return axis


MIN_R_DEFAULT = 100
MAX_R_DEFAULT = 1000


def time_ring(
    g: Plottable,
    time_col: Optional[str] = None,
    num_rings: Optional[int] = None,
    time_start: Optional[np.datetime64] = None,
    time_end: Optional[np.datetime64] = None,
    time_unit: Optional[TimeUnit] = None,
    min_r: float = MIN_R_DEFAULT,
    max_r: float = MAX_R_DEFAULT,
    reverse: bool = False,
    format_axis: Optional[Callable[[List[Dict]], List[Dict]]] = None,
    format_label: Optional[Callable[[np.datetime64, int, np.timedelta64], str]] = None,
    play_ms: int = 2000
) -> Plottable:
    """Radial graph layout where nodes are positioned based on a datetime64-typed column time_col

    Uses GPU when cudf nodes are used, otherwise pandas
 with custom start and end times**
    Parameters

        :g: Plottable
        :time_col: Optional[str] Column name of nodes datetime64-typed column; defaults to first node datetime64 column
        :num_rings: Optional[int] Number of rings
        :time_start: Optional[np.datetime64] First ring and axis label
        :time_end: Optional[np.datetime64] Last ring and axis label
        :time_unit: Optional[TimeUnit] Time unit for axis labels
        :min_r: float Minimum radius, default 100
        :max_r: float Maximum radius, default 1000
        :reverse: bool Reverse the direction of the rings in terms of time
        :format_axis: Optional[Callable[[List[Dict]], List[Dict]]] Optional transform function to format axis
        :format_label: Optional[Callable[[np.datetime64, int, np.timedelta64], str]] Optional transform function to format axis label text based on axis time, ring number, and ring duration width
        :play_ms: initial layout time in milliseconds, default 2000

    :returns: Plotter
    :rtype: Plotter


    **Example: Minimal time ring layout**

    ::

            g.time_ring().plot()

    **Example: Time ring layout**

    ::

            assert 'datetime64' in g._nodes.my_time_col.dtype.name
            g2 = g.time_ring('my_time_col')
            g2.plot()        

    **Example: Time ring layout with 7 rings**

    ::

            assert 'datetime64' in g._nodes.my_time_col.dtype.name
            g2 = g.time_ring('my_time_col', num_rings=7)
            g2.plot()
    
    **Example: Time ring layout using days**

    ::

            assert 'datetime64' in g._nodes.my_time_col.dtype.name
            g2 = g.time_ring('my_time_col', time_unit='D')
            g2.plot()

    **Example: Time ring layout without labels**

    ::

            assert 'datetime64' in g._nodes.my_time_col.dtype.name
            EMPTY_AXIS_LIST = []
            g2 = g.time_ring('my_time_col', format_labels=lambda axis: EMPTY_AXIS_LIST)

    **Example: Time ring layout with specific first and last ring positions**

    ::

            assert 'datetime64' in g._nodes.my_time_col.dtype.name
            g2 = g.time_ring('my_time_col', min_r=200, max_r=2000)
            g2.plot()

    **Example: Time ring layout in reverse order**

    ::

            assert 'datetime64' in g._nodes.my_time_col.dtype.name  
            g2 = g.time_ring('my_time_col', reverse=True)
            g2.plot()


    """

    if g._nodes is None:
        raise ValueError('Expected nodes table')

    if time_col is None:
        for col in g._nodes.columns:
            if 'datetime' in g._nodes[col].dtype.name:
                time_col = col
                break
        if time_col is None:
            raise ValueError('No time_col provided and no datetime[*] dtype node column found')

    if not isinstance(time_col, str):
        raise ValueError('time_col should be a string')

    if 'datetime64' not in g._nodes[time_col].dtype.name:
        raise ValueError(f'time_col must be datetime64, received {time_col}::{g._nodes.dtypes}')

    s = g._nodes[time_col].astype('datetime64[ns]')
    sf = s.astype('int64')

    print('=================================================')
    (
        round_unit,
        rounded_step_dur,
        rounded_set_offset,
        time_start_rounded,
        time_end_rounded,
        num_rings
    ) = time_stats(s, num_rings, time_start=time_start, time_end=time_end, time_unit=time_unit)

    sf_max = time_end_rounded.astype('datetime64[ns]').astype('int64')
    sf_min = time_start_rounded.astype('datetime64[ns]').astype('int64')
    scalar = (max_r - min_r) / (sf_max - sf_min)
    r = (sf - sf_min) * scalar + min_r  # (min_r + (max_r - min_r) / num_rings)

    print('round_unit', round_unit)
    print('rounded_step_dur', rounded_step_dur)
    print('rounded_set_offset', rounded_set_offset)
    print('time_start_rounded', time_start_rounded)
    print('time_end_rounded', time_end_rounded)
    print('s_min', s.min())
    print('s_max', s.max())

    if reverse:
        r = -r + (max_r + min_r)

    idx = r.reset_index(drop=True).index.to_series()
    if 'cudf' in str(g._nodes.__class__):
        import cudf
        x = r * cudf.Series(np.cos(idx))
        y = r * cudf.Series(np.sin(idx))
    else:
        x = r * pd.Series(np.cos(idx))
        y = r * pd.Series(np.sin(idx))

    axis = gen_axis(
        num_rings,
        time_start_rounded,
        rounded_step_dur,
        rounded_set_offset,
        round_unit,
        min_r,
        max_r,
        scalar,
        format_label,
        reverse=reverse
    )

    if format_axis is not None:
        axis = format_axis(axis)

    #print('axis', axis)

    g2 = (
        g
          .nodes(lambda g: g._nodes.assign(x=x, y=y, r=r))
          .encode_axis(axis)
          .settings(url_params={
              'play': play_ms,
              'lockedR': True,
              'bg': '%23E2E2E2'  # Light grey due to labels being fixed to dark
          })
          .encode_point_color(time_col, ['blue', 'yellow', 'red'], as_continuous=True)  # type: ignore
    )

    return g2

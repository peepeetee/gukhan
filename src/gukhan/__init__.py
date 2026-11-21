# SPDX-License-Identifier: Apache-2.0
"""gukhan: Hangul to Hanja mixed-script (國漢混用) converter.

The public API is what this module exports in ``__all__``; see ``docs/api-policy.md`` for what is
stable and how a change is announced. 公開 API는 ``__all__``에 있는 것뿐이며, 變更 方針은
``docs/api-policy.md``에 있습니다.

    >>> from gukhan import Converter
    >>> Converter().convert("국군은 작전 계획을 수립하였다.").text  # doctest: +SKIP

The one-shot helper is ``gukhan.convert.convert``: the package deliberately does not re-export it, because the
name would hide the ``gukhan.convert`` module. 한 번에 쓰는 ``convert``는 ``gukhan.convert.convert``에 있으며,
module 이름을 가리지 않도록 일부러 여기서 다시 내보내지 않습니다.
"""

__version__ = "0.0.0"

from .analyser import Analyser, KiwiAnalyser, ListAnalyser, Token
from .convert import Converter, Decision, Kind, Result
from .lexicon import Entry, Lexicon
from .overrides import Overrides

__all__ = [
    "Analyser",
    "Converter",
    "Decision",
    "Entry",
    "Kind",
    "KiwiAnalyser",
    "Lexicon",
    "ListAnalyser",
    "Overrides",
    "Result",
    "Token",
    "__version__",
]

# Class base Preprocessors

from .base import Preprocessor
from .convertfigures import ConvertFiguresPreprocessor
from .svg2pdf import SVG2PDFPreprocessor
from .extractoutput import ExtractOutputPreprocessor
from .latex import LatexPreprocessor
from .csshtmlheader import CSSHTMLHeaderPreprocessor
from .highlightmagics import HighlightMagicsPreprocessor
from .clearoutput import ClearOutputPreprocessor
from .execute import ExecutePreprocessor, CellExecutionError
from .regexremove import RegexRemovePreprocessor
from .tagremove import TagRemovePreprocessor

# decorated function Preprocessors
from .coalescestreams import coalesce_streams

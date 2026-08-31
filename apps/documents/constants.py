PDF_EXTENSION = ".pdf"
PLAIN_TEXT_EXTENSIONS = frozenset({".txt", ".md", ".markdown"})
ALLOWED_UPLOAD_EXTENSIONS = frozenset({PDF_EXTENSION, *PLAIN_TEXT_EXTENSIONS})
INVALID_FORMAT_ERROR = "Invalid file format. Only PDF, TXT, and Markdown files are allowed."

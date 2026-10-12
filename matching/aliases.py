"""Central title aliases, in precedence order. Avoid generic engineer/data keyword guesses."""

ROLE_ALIASES = [
    (
        "Other",
        (
            r"^(?!.*\b(?:software (?:engineer|developer)|machine learning engineer|"
            r"implementation (?:consultant|engineer|specialist)|support engineer|"
            r"(?:data|database|network|systems|cloud) (?:engineer|architect|administrator)|"
            r"solutions? (?:engineer|architect)|devops|site reliability)\b).*"
            "\\b(?:counsel|legal|recruiter|recruiting|account ex"
            "ecutive|marketing|finance|financial|sales operatio"
            "ns|sales support|administrative|nurse|mechanical|e"
            "lectrical|civil|manufacturing|industrial|hardware|"
            "firmware)\\b"
        ),
    ),
    ("Product Support", r"\b(?:product|platform) support(?: engineer| specialist| analyst)?\b"),
    ("Application Support", r"\b(?:application support|application analyst)\b"),
    (
        "Technical Support",
        (
            "\\b(?:technical support|customer support engineer|s"
            "upport engineer|technical services engineer|tse|he"
            "lpdesk engineer)\\b"
        ),
    ),
    (
        "Solutions Engineering",
        (
            "\\b(?:solutions? engineer|solutions? architect|sale"
            "s engineer|pre sales|customer engineer|field engin"
            "eer)\\b"
        ),
    ),
    ("Implementation", r"\b(?:implementation|integration (?:engineer|consultant))\b"),
    (
        "QA / Testing",
        (
            "\\b(?:qa|quality assurance|sdet|software test(?:er|"
            "ing)?|test engineer|test analyst|testing engineer)"
            "\\b"
        ),
    ),
    ("Mobile", r"\b(?:mobile|ios|android|react native)\b"),
    ("Front-End", r"\bfront ?end\b"),
    ("Full-Stack", r"\bfull ?stack\b"),
    ("Back-End", r"\bback ?end\b"),
    ("Database", r"\b(?:database|dba|postgres(?:ql)? engineer)\b"),
    ("DevOps / SRE", r"\b(?:devops|site reliability|sre|production engineer|release engineer)\b"),
    (
        "Networking",
        r"\b(?:network(?:ing)? (?:engineer|administrator|analyst)|network operations)\b",
    ),
    (
        "Cybersecurity",
        (
            "\\b(?:cybersecurity|security (?:engineer|analyst|ar"
            "chitect|operations)|information security|soc analy"
            "st|penetration test)\\b"
        ),
    ),
    (
        "Systems / Business Systems",
        r"\b(?:business systems|systems analyst|systems engineer|business analyst)\b",
    ),
    (
        "Cloud / Infrastructure",
        r"\b(?:cloud|infrastructure|systems administrator|platform engineer)\b",
    ),
    (
        "IT Support",
        (
            "\\b(?:it (?:support|analyst|engineer|technician)|he"
            "lp desk|service desk|technology analyst|desktop su"
            "pport)\\b"
        ),
    ),
    (
        "Data / Analytics",
        (
            "\\b(?:data (?:engineer|analyst|scientist|science)|a"
            "nalytics|machine learning|ml engineer|ai engineer|"
            "applied ai|research (?:engineer|scientist))\\b"
        ),
    ),
    (
        "Software Engineering",
        (
            "\\b(?:software|developer|application developer|forw"
            "ard deployed|product engineer|performance engineer"
            "|fullstack|backend|frontend)\\b"
        ),
    ),
]
ROLE_FAMILIES = [
    "Software Engineering",
    "Front-End",
    "Back-End",
    "Full-Stack",
    "Mobile",
    "QA / Testing",
    "Technical Support",
    "Product Support",
    "Application Support",
    "Implementation",
    "Solutions Engineering",
    "Systems / Business Systems",
    "Cloud / Infrastructure",
    "IT Support",
    "DevOps / SRE",
    "Data / Analytics",
    "Cybersecurity",
    "Database",
    "Networking",
    "Other",
]
EARLY_LEVELS = {"internship", "new_grad", "entry", "junior", "associate", "early_career", "level_1"}
SENIOR_LEVELS = {"senior", "staff", "principal", "lead", "manager", "director", "executive"}

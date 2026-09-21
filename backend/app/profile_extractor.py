import re

# Each skill maps to other names people write for it.
SKILLS: dict[str, list[str]] = {
    # Programming languages
    "python": [],
    "java": [],
    "c": ["c programming", "c language", "c/c++"],
    "c++": ["cpp"],
    "c#": ["csharp"],
    "javascript": ["es6"],
    "typescript": [],
    "go": ["golang"],
    "rust": [],
    "kotlin": [],
    "swift": [],
    "php": [],
    "ruby": [],
    "scala": [],
    "r": ["r programming", "rstudio"],
    "matlab": [],
    "dart": [],
    "bash": ["shell scripting", "shell script"],
    "powershell": [],
    "sql": [],
    "pl/sql": ["plsql"],
    "html": ["html5"],
    "css": ["css3"],
    # Web and backend
    "react": ["react.js", "reactjs", "react js"],
    "angular": ["angularjs"],
    "vue": ["vue.js", "vuejs"],
    "next.js": ["nextjs"],
    "node.js": ["nodejs", "node js"],
    "express.js": ["expressjs", "express js"],
    "django": [],
    "flask": [],
    "fastapi": [],
    "spring boot": ["springboot", "spring framework"],
    "asp.net": ["asp net"],
    ".net": ["dotnet", ".net core"],
    "laravel": [],
    "bootstrap": [],
    "tailwind css": ["tailwind", "tailwindcss"],
    "jquery": [],
    "redux": [],
    "rest api": ["rest apis", "restful api", "restful apis", "restful services"],
    "graphql": [],
    "websockets": ["websocket", "web sockets"],
    "microservices": ["microservice"],
    "full stack": ["fullstack", "full-stack"],
    # AI, ML and data
    "machine learning": ["ml"],
    "deep learning": [],
    "nlp": ["natural language processing"],
    "computer vision": [],
    "generative ai": ["genai", "gen ai", "generative artificial intelligence"],
    "llm": ["llms", "large language model", "large language models"],
    "rag": ["retrieval-augmented generation", "retrieval augmented generation"],
    "embeddings": ["embedding", "vector embeddings"],
    "semantic search": [],
    "prompt engineering": [],
    "langchain": [],
    "llamaindex": ["llama index"],
    "hugging face": ["huggingface"],
    "transformers": [],
    "openai": ["openai api"],
    "vector database": ["vector db", "faiss", "pinecone", "chromadb"],
    "tensorflow": [],
    "pytorch": [],
    "keras": [],
    "scikit-learn": ["sklearn", "scikit learn"],
    "pandas": [],
    "numpy": [],
    "scipy": [],
    "matplotlib": [],
    "seaborn": [],
    "opencv": [],
    "nltk": [],
    "spacy": [],
    "xgboost": [],
    "streamlit": [],
    "jupyter": ["jupyter notebook"],
    "data analysis": ["data analytics"],
    "data visualization": ["data visualisation"],
    "data structures": ["dsa"],
    "algorithms": [],
    "statistics": [],
    "power bi": ["powerbi"],
    "tableau": [],
    "excel": ["ms excel", "microsoft excel", "advanced excel"],
    "etl": [],
    "spark": ["apache spark", "pyspark"],
    "hadoop": [],
    "kafka": ["apache kafka"],
    "airflow": ["apache airflow"],
    # Databases
    "mysql": [],
    "postgresql": ["postgres"],
    "mongodb": ["mongo db"],
    "sqlite": [],
    "oracle": ["oracle db"],
    "sql server": ["mssql", "ms sql"],
    "redis": [],
    "elasticsearch": [],
    "firebase": [],
    "dynamodb": [],
    "cassandra": [],
    # DevOps, cloud and tools
    "docker": [],
    "kubernetes": ["k8s"],
    "jenkins": [],
    "terraform": [],
    "ansible": [],
    "git": [],
    "github": [],
    "gitlab": [],
    "bitbucket": [],
    "github actions": [],
    "ci/cd": ["cicd", "ci cd", "continuous integration"],
    "aws": ["amazon web services"],
    "azure": ["microsoft azure"],
    "gcp": ["google cloud"],
    "linux": [],
    "nginx": [],
    "nagios": [],
    "prometheus": [],
    "grafana": [],
    "helm": [],
    "maven": [],
    "gradle": [],
    "vercel": [],
    "heroku": [],
    "netlify": [],
    "vs code": ["vscode", "visual studio code"],
    "intellij": ["intellij idea"],
    "eclipse": [],
    "pycharm": [],
    "figma": [],
    "postman": [],
    "jira": [],
    "salesforce": [],
    # Testing
    "selenium": [],
    "pytest": [],
    "junit": [],
    "jest": [],
    "cypress": [],
    "unit testing": [],
    "test automation": ["automation testing", "automated testing"],
    # Methodologies and concepts
    "agile": [],
    "scrum": [],
    "kanban": [],
    "oop": ["object-oriented programming", "object oriented programming"],
    "design patterns": [],
    "system design": [],
    # Mobile and other
    "android": [],
    "flutter": [],
    "react native": [],
    "blockchain": [],
}

# These names are also normal English words or single letters, so the plain
# name is never matched on its own. Only the aliases (and special rules) are.
ALIAS_ONLY = {"c", "r", "go", "excel", "express.js"}

# Single-letter skills are found only when written like "Languages: C, Java".
CASE_SENSITIVE_NAMES = {"c": "C", "r": "R", "go": "Go"}

# Long skills are also searched in text with the spaces removed, because
# PDF extraction sometimes runs words together (e.g. "GitHubActionsworkflows").
MIN_SQUASH_LENGTH = 8
ALWAYS_SQUASH = {"pytest"}

ROLE_KEYWORDS = [
    "software engineer", "software developer", "data scientist", "data analyst",
    "machine learning engineer", "ai engineer", "backend developer",
    "frontend developer", "full stack developer", "web developer",
]


def skill_variants(skill: str) -> list[str]:
    aliases = SKILLS.get(skill, [])
    return aliases if skill in ALIAS_ONLY else [skill] + aliases


def word_pattern(name: str) -> str:
    return r"(?<![a-z0-9])" + re.escape(name) + r"(?![a-z0-9])"


def squash(text: str) -> str:
    return re.sub(r"[^a-z0-9+#]", "", text)


def has_single_letter_skill(skill: str, text: str) -> bool:
    letter = CASE_SENSITIVE_NAMES[skill]
    pattern = r"(?<=[:,(/] )" + re.escape(letter) + r"(?=\s*[,;)/]|\s*$)"
    return re.search(pattern, text, re.MULTILINE) is not None


def extract_email(text: str) -> str | None:
    match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    return match.group(0) if match else None


def extract_skills(text: str) -> list[str]:
    text_lower = text.lower()
    compact = squash(text_lower)
    found = []

    for skill in SKILLS:
        variants = skill_variants(skill)

        matched = any(re.search(word_pattern(v), text_lower) for v in variants)

        if not matched and skill in CASE_SENSITIVE_NAMES:
            matched = has_single_letter_skill(skill, text)

        if not matched:
            for variant in variants:
                squashed = squash(variant)
                long_enough = len(squashed) >= MIN_SQUASH_LENGTH or skill in ALWAYS_SQUASH
                if long_enough and squashed in compact:
                    matched = True
                    break

        if matched:
            found.append(skill)
    return found


def extract_roles(text: str) -> list[str]:
    text_lower = text.lower()
    return [role for role in ROLE_KEYWORDS if role in text_lower]


def build_profile(text: str) -> dict:
    return {
        "email": extract_email(text),
        "skills": extract_skills(text),
        "roles": extract_roles(text),
    }

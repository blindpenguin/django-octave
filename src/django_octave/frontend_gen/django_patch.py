"""Patch Django project files for Vue frontend (CORS, JWT email obtain, register)."""

from __future__ import annotations

import re
from pathlib import Path

_ENV_MARKER_BEGIN = "# --- django-octave frontend begin ---"
_ENV_MARKER_END = "# --- django-octave frontend end ---"
_URLS_IMPORT_BEGIN = "# --- django-octave frontend imports begin ---"
_URLS_IMPORT_END = "# --- django-octave frontend imports end ---"

_DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:8080,http://127.0.0.1:8080"
)

AUTH_API_MODULE = '''"""Auth API for the Vue frontend (email JWT + optional register)."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

User = get_user_model()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT obtain using the custom user email field as username."""


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class UserListSerializer(serializers.ModelSerializer):
    """Minimal user row for FK selects in the SPA."""

    label = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "label")

    def get_label(self, obj: object) -> str:
        return str(obj)


class UserListView(ListAPIView):
    """Authenticated list of users for frontend FK dropdowns."""

    permission_classes = [IsAuthenticated]
    serializer_class = UserListSerializer
    queryset = User.objects.all().order_by("email")


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data: dict) -> object:
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):  # type: ignore[no-untyped-def]
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"email": user.email}, status=status.HTTP_201_CREATED)
'''


class DjangoPatchError(ValueError):
    """Raised when Django patches cannot complete safely."""


def build_frontend_env_block() -> str:
    return f"""
{_ENV_MARKER_BEGIN}
# Vite (5173) and prod SPA nginx (8080) origins for the Vue frontend
CORS_ALLOWED_ORIGINS={_DEFAULT_CORS_ORIGINS}
{_ENV_MARKER_END}
"""


def register_endpoint_present(root: Path) -> bool:
    """True if a register URL is already wired in ``config/urls.py``."""
    urls = root / "config" / "urls.py"
    if not urls.is_file():
        return False
    text = urls.read_text(encoding="utf-8")
    return "api/auth/register" in text


def users_list_endpoint_present(root: Path) -> bool:
    """True if ``api/users/`` is wired for FK selects."""
    urls = root / "config" / "urls.py"
    if not urls.is_file():
        return False
    return "api/users/" in urls.read_text(encoding="utf-8")


def _merge_cors_line(existing: str) -> str:
    wanted = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    parts = [p.strip() for p in existing.split(",") if p.strip()]
    for origin in wanted:
        if origin not in parts:
            parts.append(origin)
    return ",".join(parts)


def patch_env_cors(env_path: Path, *, force: bool = False) -> None:
    """Ensure ``.env.example`` lists Vite/SPA CORS origins."""
    block = build_frontend_env_block().strip("\n") + "\n"
    if not env_path.exists():
        env_path.write_text(block.lstrip("\n"), encoding="utf-8")
        return

    text = env_path.read_text(encoding="utf-8")
    if _ENV_MARKER_BEGIN in text:
        if not force:
            return
        start = text.index(_ENV_MARKER_BEGIN)
        end = text.index(_ENV_MARKER_END) + len(_ENV_MARKER_END)
        if end < len(text) and text[end] == "\n":
            end += 1
        env_path.write_text(text[:start] + block + text[end:], encoding="utf-8")
        return

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    replaced = False
    for line in lines:
        if line.startswith("CORS_ALLOWED_ORIGINS="):
            raw = line.split("=", 1)[1].strip()
            merged = _merge_cors_line(raw)
            out.append(f"CORS_ALLOWED_ORIGINS={merged}\n")
            replaced = True
        else:
            out.append(line if line.endswith("\n") else f"{line}\n")
    if not replaced:
        out.append(block)
    env_path.write_text("".join(out), encoding="utf-8")


def write_auth_api(root: Path, *, force: bool = False) -> Path:
    """Write ``apps/users/auth_api.py`` with email JWT, user list, RegisterView."""
    users = root / "apps" / "users"
    if not users.is_dir():
        raise DjangoPatchError(f"apps/users not found under {root}")
    path = users / "auth_api.py"
    if path.is_file() and not force:
        existing = path.read_text(encoding="utf-8")
        if "class UserListView" in existing and "def get_label" in existing:
            return path
        # Older auth_api — upgrade in place (UserListView / label)
    path.write_text(AUTH_API_MODULE, encoding="utf-8")
    return path


def _import_block(*, include_register: bool) -> str:
    lines = [
        _URLS_IMPORT_BEGIN,
        "from apps.users.auth_api import EmailTokenObtainPairView, UserListView",
    ]
    if include_register:
        lines.append("from apps.users.auth_api import RegisterView")
    lines.append(_URLS_IMPORT_END)
    return "\n".join(lines) + "\n"


def patch_urls(root: Path, *, include_register: bool, force: bool = False) -> Path:
    """Wire email JWT obtain, user list, and optional register into ``config/urls.py``."""
    urls_path = root / "config" / "urls.py"
    if not urls_path.is_file():
        raise DjangoPatchError(f"Missing {urls_path}")

    text = urls_path.read_text(encoding="utf-8")
    skip_register = include_register and register_endpoint_present(root) and (
        _URLS_IMPORT_BEGIN not in text
    )
    wire_register = include_register and not skip_register

    # Strip previous frontend import marker block
    if _URLS_IMPORT_BEGIN in text:
        start = text.index(_URLS_IMPORT_BEGIN)
        end = text.index(_URLS_IMPORT_END) + len(_URLS_IMPORT_END)
        if end < len(text) and text[end] == "\n":
            end += 1
        text = text[:start] + text[end:]

    # Normalize simplejwt import: keep TokenRefreshView only
    text = re.sub(
        r"from rest_framework_simplejwt\.views import [^\n]+\n",
        "from rest_framework_simplejwt.views import TokenRefreshView\n",
        text,
        count=1,
    )

    # Insert frontend imports after simplejwt import
    refresh_import = "from rest_framework_simplejwt.views import TokenRefreshView\n"
    if refresh_import not in text:
        raise DjangoPatchError("Could not find simplejwt TokenRefreshView import")
    insert_at = text.index(refresh_import) + len(refresh_import)
    text = (
        text[:insert_at]
        + _import_block(include_register=wire_register)
        + text[insert_at:]
    )

    # Replace stock obtain view with email obtain view
    text = re.sub(
        r'path\(\s*"api/auth/token/"\s*,\s*TokenObtainPairView\.as_view\(\)\s*,'
        r'\s*name\s*=\s*"token_obtain_pair"\s*\)',
        'path("api/auth/token/", EmailTokenObtainPairView.as_view(), '
        'name="token_obtain_pair")',
        text,
    )
    if "EmailTokenObtainPairView" not in text:
        if 'path("api/auth/token/"' not in text:
            raise DjangoPatchError("Could not find api/auth/token/ path")
        text = re.sub(
            r'path\(\s*"api/auth/token/"\s*,\s*[^,]+,\s*name\s*=\s*"token_obtain_pair"\s*\)',
            'path("api/auth/token/", EmailTokenObtainPairView.as_view(), '
            'name="token_obtain_pair")',
            text,
        )

    # Remove managed register / users list paths, then re-add
    text = re.sub(
        r'\n?\s*path\(\s*"api/auth/register/"\s*,\s*RegisterView\.as_view\(\)\s*,'
        r'\s*name\s*=\s*"auth_register"\s*\),?',
        "",
        text,
    )
    text = re.sub(
        r'\n?\s*path\(\s*"api/users/"\s*,\s*UserListView\.as_view\(\)\s*,'
        r'\s*name\s*=\s*"user_list"\s*\),?',
        "",
        text,
    )

    match = re.search(
        r'path\(\s*"api/auth/token/refresh/"\s*,[^\n]+\n',
        text,
    )
    if not match:
        raise DjangoPatchError("Could not find token refresh path")
    insert_parts: list[str] = []
    if wire_register:
        insert_parts.append(
            '    path("api/auth/register/", RegisterView.as_view(), '
            'name="auth_register"),\n'
        )
    insert_parts.append(
        '    path("api/users/", UserListView.as_view(), name="user_list"),\n'
    )
    end = match.end()
    text = text[:end] + "".join(insert_parts) + text[end:]

    if not force and skip_register and include_register:
        pass

    urls_path.write_text(text, encoding="utf-8")
    return urls_path


def ensure_user_list_api(root: Path) -> list[Path]:
    """Ensure ``UserListView`` + ``/api/users/`` exist (for CRUD User FK selects)."""
    root = root.resolve()
    include_register = register_endpoint_present(root)
    written: list[Path] = []
    written.append(write_auth_api(root, force=False))
    written.append(patch_urls(root, include_register=include_register, force=False))
    return written


def patch_django_for_frontend(
    root: Path,
    *,
    include_register: bool,
    force: bool = False,
) -> list[Path]:
    """Apply CORS env, auth_api module, and urls wiring. Returns touched paths."""
    root = root.resolve()
    written: list[Path] = []

    env_example = root / ".env.example"
    patch_env_cors(env_example, force=force)
    written.append(env_example)

    auth_api = write_auth_api(root, force=force)
    written.append(auth_api)

    urls = patch_urls(root, include_register=include_register, force=force)
    written.append(urls)

    return written

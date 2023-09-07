import abc

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser, AnonymousUser, PermissionsMixin
from django.contrib.auth.models import UserManager as _UserManager
from django.db import models
from django.utils.translation import gettext, gettext_lazy

from apps.account.constants import UserTypeChoices
from core.constants import SHORT_CHAR_LENGTH
from core.models import SoftDeletedManager, SoftDeletedModel


class UserManager(SoftDeletedManager, _UserManager):
    """
    User Manager
    """

    def create_user(self, username, nick_name=None, password=None, **extra_fields):
        if not username:
            raise ValueError(gettext("Username Cannot be Empty"))
        user = self.model(username=username, nick_name=nick_name, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, nick_name=None, password=None, **extra_fields):
        extra_fields["is_superuser"] = True
        self.create_user(username, nick_name, password, **extra_fields)


class User(SoftDeletedModel, AbstractBaseUser, PermissionsMixin):
    """
    User
    """

    username = models.CharField(
        gettext_lazy("username"),
        max_length=SHORT_CHAR_LENGTH,
        primary_key=True,
        validators=[AbstractUser.username_validator],
        error_messages={"unique": gettext_lazy("already in use")},
    )
    nick_name = models.CharField(gettext_lazy("Nick Name"), max_length=SHORT_CHAR_LENGTH, blank=True, null=True)
    user_type = models.CharField(
        gettext_lazy("User Type"),
        choices=UserTypeChoices.choices,
        max_length=SHORT_CHAR_LENGTH,
        default=UserTypeChoices.PERSONAL.value,
    )
    date_joined = models.DateTimeField(gettext_lazy("Date Joined"), auto_now_add=True)
    is_staff = models.BooleanField(gettext_lazy("Is Staff"), default=False)

    USERNAME_FIELD = "username"
    objects = UserManager()
    _objects = _UserManager()

    class Meta:
        verbose_name = gettext_lazy("User")
        verbose_name_plural = verbose_name
        ordering = ["username"]


class CustomAnonymousUser(AnonymousUser, abc.ABC):
    """
    Anonymous User
    """

    nick_name = "AnonymousUser"
    user_type = UserTypeChoices.PLATFORM.value

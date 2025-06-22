from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="邮箱")
    phone = forms.CharField(max_length=11, required=False, label="手机号")
    address = forms.CharField(widget=forms.Textarea, required=False, label="地址")

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2", "phone", "address"]

class CustomAuthenticationForm(AuthenticationForm):
    class Meta:
        model = User
        fields = ["username", "password"]
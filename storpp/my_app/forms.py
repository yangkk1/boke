# my_app/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class CustomUserCreationForm(UserCreationForm):
    phone = forms.CharField(max_length=11, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    avatar = forms.ImageField(required=False)

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2', 'phone', 'address', 'avatar']
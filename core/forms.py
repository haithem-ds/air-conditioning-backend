from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import Client

class ClientChangeForm(forms.ModelForm):
    """
    Custom form for changing client information including password
    """
    
    class Meta:
        model = Client
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # For existing clients, show a readonly password hash field
        if self.instance.pk:
            self.fields['password'] = ReadOnlyPasswordHashField(
                label="Password",
                help_text="Password is hashed for security. Use the 'Change Password' button below to change it."
            )
        else:
            # For new clients, show a regular password field
            self.fields['password'] = forms.CharField(
                widget=forms.PasswordInput,
                help_text="Enter password for this client"
            )
    
    def save(self, commit=True):
        client = super().save(commit=False)
        
        # Only hash password for new clients
        if not self.instance.pk and 'password' in self.cleaned_data:
            password = self.cleaned_data['password']
            if password:
                client.set_password(password)
        
        if commit:
            client.save()
        return client

class ClientPasswordChangeForm(forms.Form):
    """
    Form specifically for changing client password
    """
    password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput,
        help_text="Enter the new password"
    )
    password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput,
        help_text="Enter the same password again for verification"
    )
    
    def __init__(self, client, *args, **kwargs):
        self.client = client
        super().__init__(*args, **kwargs)
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("The two password fields didn't match.")
        
        return password2
    
    def save(self):
        password = self.cleaned_data['password1']
        self.client.set_password(password)
        self.client.save()
        return self.client

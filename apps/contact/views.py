from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import redirect, render

from .forms import ContactInquiryForm


def contact_page(request):
    if request.method == 'POST':
        form = ContactInquiryForm(request.POST)
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.site = get_current_site(request)
            inquiry.save()
            messages.success(request, 'Sua mensagem foi enviada. Entraremos em contato em breve!')
            return redirect('contact:page')
    else:
        form = ContactInquiryForm()

    return render(request, 'contact/contact_page.html', {'form': form})

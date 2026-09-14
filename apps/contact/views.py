from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import redirect, render

from apps.school.courses import find_course

from .forms import ContactInquiryForm


def contact_page(request):
    if request.method == 'POST':
        form = ContactInquiryForm(request.POST, request=request)
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.site = get_current_site(request)
            inquiry.save()
            messages.success(request, 'Sua mensagem foi enviada. Entraremos em contato em breve!')
            return redirect('contact:page')
        course = find_course(request.POST.get('course_interest', ''))
    else:
        # O card de um curso em Cursos chega com ?curso=<slug>: o formulário já traz o curso e o assunto de cursos.
        course = find_course(request.GET.get('curso', ''))
        initial = {'course_interest': course['slug'], 'subject': 'admissions'} if course else None
        form = ContactInquiryForm(request=request, initial=initial)

    return render(request, 'contact/contact_page.html', {'form': form, 'selected_course': course})

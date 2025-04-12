from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, Http404, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction, IntegrityError
from .models import ФизическиеЛица, СеансыФильмов, МестаВЗале, КупленныеБилеты
from .utils import generate_ticket_pdf, send_ticket_email
import json
import os
# <<<--- Добавьте эту функцию --->>>
def home_view(request):
    # Здесь можно получить список ближайших сеансов, например
    # upcoming_sessions = СеансыФильмов.objects.filter(время_начала__gte=timezone.now()).order_by('время_начала')[:10]
    # context = {'sessions': upcoming_sessions}
    context = {'welcome_message': 'Добро пожаловать в систему продажи билетов!'} # Простой контекст для начала
    return render(request, 'cinema_tickets/home.html', context)
# Пример View для "покупки" билета (упрощенный)
# Ожидает POST запрос с JSON: {"client_id": ID, "session_id": ID, "seat_number": номер}
@csrf_exempt
@require_POST
@transaction.atomic
def purchase_ticket_view(request):
    try:
        data = json.loads(request.body)
        client_id = data.get('client_id')
        session_id = data.get('session_id')
        seat_number = data.get('seat_number')
        # <-- Получаем email из запроса -->
        client_email = data.get('client_email')

        # <-- Обновляем проверку входных данных -->
        if not all([client_id, session_id, seat_number, client_email]):
            missing = [k for k, v in {'client_id': client_id, 'session_id': session_id, 'seat_number': seat_number, 'client_email': client_email}.items() if not v]
            return JsonResponse({'error': f'Не все поля предоставлены. Отсутствуют: {", ".join(missing)}'}, status=400)

        # <-- Валидация email -->
        try:
            validate_email(client_email)
        except ValidationError:
             return JsonResponse({'error': 'Некорректный формат email адреса.'}, status=400)


        клиент = get_object_or_404(ФизическиеЛица, pk=client_id)
        сеанс = get_object_or_404(СеансыФильмов, pk=session_id)
        место = get_object_or_404(МестаВЗале, номер_места=seat_number)

        # --- Обновление/проверка Email клиента ---
        # Если у клиента еще нет email или он отличается, обновим его
        if not клиент.email or клиент.email != client_email:
            # Проверим, не занят ли этот email другим клиентом
            if ФизическиеЛица.objects.filter(email=client_email).exclude(pk=клиент.pk).exists():
                 return JsonResponse({'error': f'Email {client_email} уже используется другим клиентом.'}, status=409) # Conflict
            клиент.email = client_email
            клиент.save() # Сохраняем обновленный email клиента

        # Проверка, не куплен ли уже билет
        if КупленныеБилеты.objects.filter(сеанс=сеанс, место=место).exists():
             return JsonResponse({'error': f'Место {seat_number} на сеанс "{сеанс.название_фильма}" уже занято.'}, status=409)

        # Создание билета
        новый_билет = КупленныеБилеты.objects.create(
            клиент=клиент,
            сеанс=сеанс,
            место=место,
            email_получателя=client_email # <-- Сохраняем email, на который отправим
        )

        # Генерация и сохранение PDF (теперь с кодами)
        try:
            generate_ticket_pdf(новый_билет)
            pdf_generated = True
        except Exception as e:
            pdf_generated = False
            print(f"Ошибка генерации PDF для билета {новый_билет.id}: {e}")
            # transaction.atomic сам откатит создание билета при ошибке здесь
            return JsonResponse({'error': 'Ошибка при генерации PDF билета.'}, status=500)

        # --- Отправка email ---
        email_sent_status = False
        if pdf_generated and новый_билет.pdf_файл:
             email_sent_status = send_ticket_email(новый_билет, client_email)
        else:
             print(f"PDF не был сгенерирован для билета {новый_билет.id}, email не отправлен.")


        # Формируем ответ
        response_data = {
            'message': 'Билет успешно куплен.',
            'ticket_id': новый_билет.id,
            'client': новый_билет.клиент.get_full_name(),
            'movie': новый_билет.сеанс.название_фильма,
            'session_time': новый_билет.сеанс.время_начала.isoformat(),
            'seat': новый_билет.место.номер_места,
            'pdf_url': request.build_absolute_uri(f'/api/tickets/{новый_билет.id}/pdf/')
        }
        if pdf_generated:
             response_data['message'] += ' PDF сгенерирован.'
        if email_sent_status:
             response_data['message'] += f' Копия отправлена на {client_email}.'
        elif pdf_generated:
             response_data['message'] += ' Не удалось отправить копию на email.'


        return JsonResponse(response_data, status=201) # 201 Created

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат JSON в теле запроса.'}, status=400)
    except ФизическиеЛица.DoesNotExist:
        return JsonResponse({'error': 'Клиент не найден.'}, status=404)
    except СеансыФильмов.DoesNotExist:
        return JsonResponse({'error': 'Сеанс не найден.'}, status=404)
    except МестаВЗале.DoesNotExist:
        return JsonResponse({'error': 'Место не найдено.'}, status=404)
    except IntegrityError as e:
        # Проверяем, связана ли ошибка с unique_together
        if 'UNIQUE constraint failed: cinema_tickets_купленныебилеты.сеанс_id, cinema_tickets_купленныебилеты.место_id' in str(e):
             # Пытаемся получить сеанс и место для сообщения об ошибке, если возможно
             seat_num_str = data.get('seat_number', '???')
             session_name_str = "???"
             try:
                 session_id_for_error = data.get('session_id')
                 if session_id_for_error:
                    session_for_error = СеансыФильмов.objects.get(pk=session_id_for_error)
                    session_name_str = f'"{session_for_error.название_фильма}"'
             except СеансыФильмов.DoesNotExist:
                 pass # Оставляем "???"
             return JsonResponse({'error': f'Место {seat_num_str} на сеанс {session_name_str} уже занято (ошибка целостности).'}, status=409)
        else:
             # Другая ошибка целостности (например, email клиента)
             print(f"Неожиданная ошибка IntegrityError при покупке билета: {e}")
             return JsonResponse({'error': 'Ошибка целостности данных при сохранении.'}, status=409)

    except Exception as e:
        print(f"Неожиданная ошибка при покупке билета: {e}")
        return JsonResponse({'error': 'Внутренняя ошибка сервера.'}, status=500)

# API View для получения PDF билета
def get_ticket_pdf_api(request, ticket_id):
    # 1. Найти билет в базе по ID
    билет = get_object_or_404(КупленныеБилеты, pk=ticket_id)

    # 2. Проверить, был ли PDF сгенерирован и сохранен для этого билета
    if not билет.pdf_файл:
        raise Http404("PDF для этого билета еще не сгенерирован или отсутствует.")

    try:
        # 3. Открыть сохраненный файл PDF из поля модели (физически лежит в MEDIA_ROOT)
        pdf = билет.pdf_файл.open('rb')
        # 4. Создать HTTP ответ с содержимым файла и правильным типом контента
        response = HttpResponse(pdf.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(билет.pdf_файл.name)}"'
        pdf.close() # Не забываем закрыть файл
        return response
    except FileNotFoundError:
         # Если запись в базе есть, а файла на диске нетcd
         raise Http404(f"Файл PDF для билета {ticket_id} не найден на сервере.")
    except Exception as e:
        print(f"Ошибка при отдаче PDF файла {билет.pdf_файл.name}: {e}")
        return HttpResponse("Ошибка при получении файла PDF.", status=500)
# cinema_tickets/utils.py

import io
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A6  # Импорт размера страницы A6
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader # Для вставки изображений
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage # Для отправки email

# Импорты для кодов
import qrcode
from barcode import get_barcode_class
from barcode.writer import ImageWriter

def generate_ticket_pdf(ticket):
    """
    Генерирует PDF для объекта КупленныеБилеты, включая QR (с информацией о билете)
    и штрихкод, и сохраняет его в поле pdf_файл.
    """
    # --- Регистрация шрифта ---
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'DejaVuSans.ttf')
    try:
        # Проверяем, зарегистрирован ли уже шрифт, чтобы избежать повторной регистрации
        # (хотя reportlab обычно сам с этим справляется)
        if 'DejaVuSans' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
    except Exception as e:
         print(f"Ошибка регистрации шрифта: {e}. Убедитесь, что файл {font_path} существует.")
         # Можно попробовать использовать стандартный шрифт как запасной вариант
         # if 'DejaVuSans' not in pdfmetrics.getRegisteredFontNames():
         #     pdfmetrics.registerFont(TTFont('DejaVuSans', 'Helvetica'))

    buffer = io.BytesIO()
    # Используем размер A6, альбомная ориентация
    page_width, page_height = A6[1], A6[0]
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))
    c.setFont('DejaVuSans', 10) # Устанавливаем основной шрифт и размер

    # --- Данные для QR-кода (ИНФОРМАЦИЯ О БИЛЕТЕ) ---
    qr_data = f"""Билет №: {ticket.id}
Фильм: {ticket.сеанс.название_фильма}
Сеанс: {ticket.сеанс.время_начала.strftime('%d.%m.%Y %H:%M')}
Место: {ticket.место.номер_места}
Клиент: {ticket.клиент.get_full_name()}"""

    # --- Данные для ШТРИХКОДА (оставляем ID) ---
    barcode_id_data = f"TICKET-{ticket.id}"

    # --- Генерация QR-кода ---
    qr_buffer = io.BytesIO()
    try:
        qr_img = qrcode.make(qr_data, error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        qr_reader = ImageReader(qr_buffer)
    except Exception as e:
        print(f"Ошибка генерации QR-кода для билета {ticket.id}: {e}")
        qr_reader = None # Не удалось создать QR

    # --- Генерация штрихкода ---
    barcode_buffer = io.BytesIO()
    barcode_reader = None # По умолчанию штрихкода нет
    try:
        Code128 = get_barcode_class('code128')
        # Убедимся, что данные только ASCII для Code128
        barcode_ascii_data = barcode_id_data.encode('ascii', errors='ignore').decode('ascii')
        if barcode_ascii_data:
            code128_barcode = Code128(barcode_ascii_data, writer=ImageWriter())
            code128_barcode.write(barcode_buffer, options={
                'module_height': 8.0, # Высота штрихов
                'write_text': False,  # Не писать текст под штрихкодом
                'text_distance': 1.0, # Расстояние текста (не используется при write_text=False)
                'quiet_zone': 2.0     # Отступы по бокам
            })
            barcode_buffer.seek(0)
            barcode_reader = ImageReader(barcode_buffer)
    except Exception as e:
        print(f"Ошибка генерации штрихкода для билета {ticket.id}: {e}")
        barcode_reader = None # Не удалось создать штрихкод

    # --- Рисуем содержимое билета ---
    margin_left = 8 * mm
    margin_right = 8 * mm
    margin_top = 8 * mm
    margin_bottom = 8 * mm
    line_height = 5 * mm
    current_y = page_height - margin_top - line_height

    # Заголовок
    c.setFont('DejaVuSans', 14)
    c.drawCentredString(page_width / 2, current_y, "Билет в кино")
    current_y -= line_height * 1.5
    c.setFont('DejaVuSans', 10) # Возвращаем основной размер шрифта

    # Основная информация (левая часть)
    info_block_y_start = current_y
    c.drawString(margin_left, current_y, f"Фильм: {ticket.сеанс.название_фильма}")
    current_y -= line_height
    c.drawString(margin_left, current_y, f"Сеанс: {ticket.сеанс.время_начала.strftime('%d.%m.%Y %H:%M')}")
    current_y -= line_height
    c.drawString(margin_left, current_y, f"Продолж.: {ticket.сеанс.продолжительность}")
    current_y -= line_height
    c.drawString(margin_left, current_y, f"Место: {ticket.место.номер_места}")
    current_y -= line_height
    c.drawString(margin_left, current_y, f"Покупатель: {ticket.клиент.get_full_name()}")
    current_y -= line_height
    if ticket.email_получателя:
         c.drawString(margin_left, current_y, f"Email: {ticket.email_получателя}")

    # --- Размещение кодов (правая часть) ---
    qr_size = 25 * mm # Размер QR-кода
    qr_x = page_width - margin_right - qr_size
    # Размещаем QR справа, примерно на уровне начала информационного блока
    qr_y = info_block_y_start - qr_size + line_height
    if qr_reader:
        try:
            c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size, mask='auto')
        except Exception as e:
            print(f"Ошибка отрисовки QR кода для билета {ticket.id}: {e}")
        finally:
             qr_buffer.close() # Закрываем буфер QR в любом случае

    barcode_height = 15 * mm
    barcode_width = 50 * mm # Ширина штрихкода
    barcode_x = page_width - margin_right - barcode_width
    barcode_y = qr_y - barcode_height - 5 * mm # Ниже QR-кода с отступом
    if barcode_reader:
        try:
            c.drawImage(barcode_reader, barcode_x, barcode_y, width=barcode_width, height=barcode_height, mask='auto')
        except Exception as e:
             print(f"Ошибка отрисовки штрихкода для билета {ticket.id}: {e}")
        finally:
            barcode_buffer.close() # Закрываем буфер штрихкода

    # --- Нижняя информация ---
    c.setFont('DejaVuSans', 7) # Мелкий шрифт для служебной информации
    c.drawRightString(page_width - margin_right, margin_bottom / 2, f"Билет №{ticket.id} | Покупка: {ticket.дата_покупки.strftime('%d.%m.%Y %H:%M')}")
    c.drawString(margin_left, margin_bottom / 2, "Приятного просмотра!")

    # --- Завершение PDF ---
    c.showPage()
    c.save()

    # --- Сохранение PDF в модель ---
    buffer.seek(0)
    pdf_data = buffer.getvalue()
    buffer.close()

    file_name = f'ticket_{ticket.id}.pdf'
    # Сохраняем PDF в поле модели. save=True обновит запись в БД.
    # Это важно, чтобы изменения (путь к файлу) сохранились
    ticket.pdf_файл.save(file_name, ContentFile(pdf_data), save=True)

    # Возвращаем путь к сохраненному файлу (может быть полезно)
    return ticket.pdf_файл.path


# --- Функция для отправки email ---
def send_ticket_email(ticket, recipient_email):
    """
    Отправляет email с PDF билетом в качестве вложения.
    """
    if not recipient_email:
        print(f"Email для билета {ticket.id} не указан. Отправка невозможна.")
        return False

    # Убедимся, что у билета есть связанный PDF файл и путь к нему
    if not ticket.pdf_файл or not hasattr(ticket.pdf_файл, 'path') or not ticket.pdf_файл.path:
        print(f"PDF файл для билета {ticket.id} отсутствует или путь не определен. Отправка email невозможна.")
        # Попробуем сгенерировать PDF заново, если его нет (на всякий случай)
        try:
            print(f"Попытка повторной генерации PDF для билета {ticket.id} перед отправкой email.")
            generate_ticket_pdf(ticket)
            if not ticket.pdf_файл or not ticket.pdf_файл.path:
                 print(f"Повторная генерация PDF не удалась. Отправка email отменена.")
                 return False
        except Exception as e:
            print(f"Ошибка при повторной генерации PDF перед отправкой email: {e}")
            return False


    subject = f"Ваш билет в кино: {ticket.сеанс.название_фильма} (Билет №{ticket.id})"
    body = f"""
Здравствуйте, {ticket.клиент.get_full_name()}!

Вы успешно приобрели билет на фильм "{ticket.сеанс.название_фильма}".

Детали сеанса:
Дата и время: {ticket.сеанс.время_начала.strftime('%d.%m.%Y %H:%M')}
Место: {ticket.место.номер_места}

Ваш электронный билет прикреплен к этому письму в формате PDF.
Пожалуйста, сохраните его или распечатайте. Его можно показать на входе в зал.

Приятного просмотра!

С уважением,
Ваш Кинотеатр
    """
    # Используем email из настроек Django
    # Убедитесь, что DEFAULT_FROM_EMAIL задан в settings.py
    from_email = settings.DEFAULT_FROM_EMAIL

    try:
        email = EmailMessage(
            subject,
            body,
            from_email,
            [recipient_email] # Адрес получателя должен быть списком
        )
        # Прикрепляем PDF файл, используя его путь
        email.attach_file(ticket.pdf_файл.path)
        email.send(fail_silently=False) # fail_silently=False вызовет исключение при ошибке отправки
        print(f"Email с билетом {ticket.id} успешно отправлен на {recipient_email}")
        return True
    except FileNotFoundError:
        print(f"Ошибка при отправке email: файл PDF для билета {ticket.id} не найден по пути {ticket.pdf_файл.path}")
        return False
    except Exception as e:
        print(f"Ошибка при отправке email для билета {ticket.id} на {recipient_email}: {e}")
        # Здесь можно добавить более детальное логирование ошибки
        return False
import wabot_settings
import requests
from loguru import logger
import mimetypes
import os

logger.add('logs.log', format="{time} {level} {message}", level="DEBUG")

format_options = {
    'bold': '*',
    'italic': '_',
    'crossed': '~',
    'code': '```'}

class WaBot:

    BASE_API_URL = wabot_settings.BASE_API_URL
    MEDIA_API_URL = wabot_settings.MEDIA_API_URL

    def __init__(self, token, number_id):
        self.token = token
        self.number_id = number_id
        self.api_url = WaBot.BASE_API_URL.format(number_id=number_id)
        self.message_handlers = {}

    def verify_webhook(self, request, verify_token):
        check = request.args.get('hub.verify_token')
        response_value = request.args.get('hub.challenge')
        if verify_token == check:
            return response_value
        return 'OK'

    def entry_point_handler(self, request):
        json_data = None
        try:
            json_data = WaBot.__get_message(request)
        except Exception as e:
            logger.exception(e)

        if not json_data:
            return

        if 'messages' in json_data:
            for message in json_data['messages']:
                logger.info(message)
                try:
                    mob_number = WaBot.__get_mobile_number(message)

                    contact_name = self.__get_contact_name(mob_number, request)
                    message['contact_name'] = contact_name

                    target = message['type']
                    if target in self.message_handlers:
                        handler = self.message_handlers[target]['handler']
                        handler(message, mob_number)

                except Exception as e:
                    logger.exception(e)

    def message_handler(self, type):
        def wrapp(func):
            self.message_handlers[type] = dict(handler=func)
            def wrapper(func):
                pass
            return wrapper
        return wrapp

    def get_file_id(self, message):
        if 'document' in message:
            return message['document']['id']
        if 'image' in message:
            return message['image']['id']

    def get_reply_id(self, message):
        if 'button_reply' in message['interactive']:
            return message['interactive']['button_reply']['id']

    def download_file(self, id):
        downl_link = WaBot.MEDIA_API_URL + '/' + id
        resp = requests.get(downl_link, headers={'Authorization': self.token})
        json_data = resp.json()

        if resp.status_code == 200:
            if 'url' not in json_data:
                return None

            download_url = json_data['url']
            resp = requests.get(download_url, headers={'Authorization': self.token})
            binary = resp.content

            file_type = json_data['mime_type'].split('/').pop()
            file_name = f'{id}.{file_type}'
            file_path = '/'.join(['static', file_name])

            with open(file_path, 'wb') as f:
                f.write(binary)
                logger.info(f'file downloaded id:{id} path:{file_path}')

            try:
                mime_type, encoding = mimetypes.guess_type(file_path)

                extension = mimetypes.guess_extension(mime_type)
                new_filename = file_name = f'{id}{extension}'
                new_path = '/'.join(['static', new_filename])

                os.rename(file_path, new_path)

                return file_name
            except:
                logger.error(f'type not found for file id:{id}')
                return None
        else:
            logger.info(f'error download file with id {id}: {str(resp)} - {resp.text}')

        return None

    def send_message(self, mob_number, text, **kwargs):
        if 'format' in kwargs:
            text = WaBot.__format_text_message(text, kwargs['format'])

        if 'type' in kwargs:
            self.__send_interactive_message(mob_number, text, **kwargs)
        else:
            self.__send_message(mob_number, text)

    def send_templates(self, mob_number, template_name, lang_code):
        context = WaBot.__init_response_context(mob_number)
        context['type'] = 'template'
        template_settings = dict(name=template_name, language=dict(code=lang_code))
        context['template'] = template_settings
        self.__send(context)

    def send_image(self, mob_number, media_url, text=None):
        context = WaBot.__init_response_context(mob_number)
        context['type'] = 'image'
        if text:
            image_data = dict(link=media_url, caption=text)
        else:
            image_data = dict(link=media_url)
        context['image'] = image_data
        self.__send(context)

    def send_document(self, mob_number, media_url, text=None):
        context = WaBot.__init_response_context(mob_number)
        context['type'] = 'document'
        if text:
            doc_data = dict(link=media_url, filename=text)
        else:
            doc_data = dict(link=media_url)
        context['document'] = doc_data
        self.__send(context)

    def send_audio(self, mob_number, media_url):
        pass

    def send_video(self, mob_number, media_url):
        pass

    def send_sticker(self):
        pass

    def __send_message(self, mob_number, text):
        context = WaBot.__init_response_context(mob_number)
        context['type'] = 'text'
        context['text'] = dict(body=text)
        self.__send(context)

    def __send_interactive_message(self, mob_number, text, media_url=None, type=None, title=None, markup=None):
        context = WaBot.__init_response_context(mob_number)
        context['type'] = 'interactive'
        context["interactive"] = {"type": "button",
                                  "body": dict(text=text)}
        WaBot.__add_markup(context, markup)
        WaBot.__add_header(context, type, media_url, title)
        self.__send(context)

    def __send(self, data):
        response = self.__request_with_auth(data)

    def __request_with_auth(self, data):
        headers = {'Content-Type': 'application/json; charset=utf-8',
                   'Authorization': self.token}
        return requests.post(self.api_url, headers=headers, json=data)

    def __get_contact_name(self, mob_number, request):
        data = self.__get_message(request)
        if 'contacts' not in data:
            return None

        for contact in data['contacts']:
            if mob_number == contact['wa_id']:
                return contact['profile']['name']

    @staticmethod
    def __get_mobile_number(message):
        if 'from' in message:
            return message['from']

    @staticmethod
    def __init_response_context(mob_number):
        return {'messaging_product': 'whatsapp',
                'to': mob_number}

    @staticmethod
    def __add_header(context, type, media_url, title):
        header = None

        if type == 'text':
            if title:
                header = dict(type=type, text=title)
        elif type:
            link = dict(link=media_url)
            header = {'type': type, type: link}

        if header:
            context["interactive"]['header'] = header

    @staticmethod
    def __get_message(request):
        return request.json['entry'][0]['changes'][0]['value']

    @staticmethod
    def __add_markup(context, markup):
        if markup and len(markup):
            buttons = []
            for b in markup:
                button_setting = dict(id=b['id'], title=b['title'])
                buttons.append(dict(type='reply', reply=button_setting))

            context['interactive']['action'] = dict(buttons=buttons)

    @staticmethod
    def __format_text_message(text, format_type):
        marker = format_options[format_type]
        return f'{marker}{str(text).strip()}{marker}'
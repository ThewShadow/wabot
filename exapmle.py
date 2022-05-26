import flask
from flask import request
from wabot import WaBot
import app_setting
import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

wabot = WaBot(token=app_setting.APP_TOKEN, number_id=app_setting.NUMBER_ID)

app = flask.Flask(__name__)


@app.route('/webhooks', methods=['GET'])
def verify_webhook():
    return wabot.verify_webhook(request, app_setting.WEBHOOK_VERIFY_TOKEN)


@app.route('/webhooks', methods=['POST'])
def entry_point():
    wabot.entry_point_handler(request)
    return 'OK'


@app.route('/', methods=['GET'])
def index():
    return 'OK'


@app.route('/static/<path:path>')
def send_file(path):
    return flask.send_from_directory('static', path)


@wabot.message_handler('image')
def image_handler(message, mob_number):
    image_id = wabot.get_file_id(message)

    local_file_name = wabot.download_file(image_id)

    wabot.send_message(mob_number, 'image recive, id' + image_id + ' image-name: ' + local_file_name)


@wabot.message_handler('document')
def document_handler(message, mob_number):
    doc_id = wabot.get_file_id(message)

    local_file_name = wabot.download_file(doc_id)

    wabot.send_message(mob_number, 'document recive id: ' + doc_id + ' file-name: ' + local_file_name)


@wabot.message_handler('interactive')
def interactive_callback(message, mob_number):
    reply_id = wabot.get_reply_id(message)

    if reply_id == 'reply_value_yes':
        wabot.send_message(mob_number, 'Yes')
    elif reply_id == 'reply_value_no':
        wabot.send_message(mob_number, 'No')

    if reply_id == 'show_demo_yes':
        show_demonstration(message, mob_number)
    else:
        wabot.send_message(mob_number, "Ok, come back when you're ready")

@wabot.message_handler('text')
def text_handler(message, mob_number):
    welcome = 'Welcome!! ' + message['contact_name']
    wabot.send_message(mob_number, welcome, format='bold')

    markup = [dict(id='show_demo_yes', title='Show me'),
              dict(id='show_demo_no', title='No, Thanks')]

    wabot.send_message(mob_number, 'Show you a demo?', type='text', markup=markup)

def show_demonstration(message, mob_number):

    file_url = flask.url_for("static", filename="text.txt")
    file_url = app_setting.THIS_HOST + file_url

    image_url = flask.url_for("static", filename="VD8ldiL.jpg")
    image_url = app_setting.THIS_HOST + image_url

    title = 'Now a demonstration of the capabilities of the bot will be made.'
    wabot.send_message(mob_number, title)

    # send document example
    wabot.send_message(mob_number, 'mesage with document example:', format='italic')
    wabot.send_document(mob_number, file_url, text='document example')

    # send image example
    wabot.send_message(mob_number, 'mesage with image example:', format='crossed')
    wabot.send_image(mob_number, image_url, text='image example')

    # define markup
    markup = [dict(id='reply_value_yes', title='yes'),
              dict(id='reply_value_no', title='no')]

    # send message with markup example
    wabot.send_message(mob_number, 'message with markup example:')
    wabot.send_message(mob_number, 'select option',
                       markup=markup,
                       type='text',
                       title='title example')

    # send message with markup image  example
    wabot.send_message(mob_number, 'message with markup image example:')
    wabot.send_message(mob_number, 'select option',
                       markup=markup,
                       type='image',
                       media_url=image_url)

    # send message with markup document example
    wabot.send_message(mob_number, 'message with markup, document example:')
    wabot.send_message(mob_number, 'select option',
                       markup=markup,
                       type='document',
                       media_url=file_url)

    # send message with template
    wabot.send_message(mob_number, 'message with template example:')
    wabot.send_templates(mob_number=mob_number,
                         template_name='hello_world',
                         lang_code='en_US')

    wabot.send_message(mob_number, "print('this example code style format')", format='code')


if __name__ == '__main__':
    host = 'localhost'
    port = 5555
    print('server started')
    app.run(host, port)


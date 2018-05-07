from config import app, publish, store, socket, fingerPrint
from flask import render_template, request, flash, redirect, url_for
from models import *
import time
from forms import UserDefineForm, UserEnrollForm

store['clients'] = []


# --------------#
#   Sockets     #
#               #
# --------------#
@socket.on('connect')
def socket_connect():
    socket.emit('auth', request.sid)
    store['clients'].append(request.sid)


@socket.on('disconnect')
def socket_disconnect():
    store['fingerPrintEnabled'] = False
    store['clients'].remove(request.sid)


@socket.on('setFingerPrintStatus')
def set_fingerprint_status(data):
    store['fingerPrintEnabled'] = data

# --------------#
#   Endpoints   #
#               #
# --------------#
@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/settings') #TODO: If no action is done on this page for about one minute, leads to Broken Pipe Eroor on terminal but yet everything works fine
def settings():
    return render_template('settings.html')

# -------------------------#
#       User Define        #
# -------------------------#
@app.route('/user_define', methods=['POST', 'GET'])
def user_define():
    # f.readImage() #TODO: sensor should be off when on this page, unless it is needed

    form = UserDefineForm()

    if request.method == 'POST':  # TODO: form validation
        # Form NOT validated
        if form.validate() == 0:  # form.validate == False
            return render_template('user_define.html', form=form)
        # Form validated correctly
        elif form.validate() != 0:  # form.validate != False
            the_first_name = request.form['first_name']
            the_last_name = request.form['last_name']
            the_code_melli = request.form['code_melli']

            # TODO: (SOLVED) code_melli existence query
            code_melli_existence_clause = db.table('users').where('code_melli', the_code_melli).count()
            # code_melli_existence_clause = 'CODE MELLI EXISTS NOT'
            # code_melli_existence_clause = db.table('users').where_exists(db.table('users').select(db.raw(1)).where_raw('users.code_melli' == 23))

            # This code melli already exists.
            if code_melli_existence_clause != 0:
                flash('This code melli already exists.')
                return render_template('user_define.html', form=form)
            # This is a new code melli.
            elif code_melli_existence_clause == 0:
                db.table('users').insert(first_name=the_first_name, last_name=the_last_name, code_melli=the_code_melli)
                flash('The user has been successfully defined.')
                return render_template('user_define.html', form=form)
    elif request.method == 'GET':
        return render_template('user_define.html', form=form)

# -------------------------#
#       User Enroll        #
# -------------------------#
@app.route('/user_enroll', methods=['POST', 'GET'])
def user_enroll():  # TODO: Seems NOT enrolling new users when sensor memory is fresh - check again

    # f.readImage() #TODO: sensor should be off when on this page, unless it is needed

    our_result = {'status': 0}

    form = UserEnrollForm()

    users = db.table('users').get()
    users_table_records_count = db.table('users').get().count()

    id_list = []
    first_name_list = []
    last_name_list = []
    code_melli_list = []
    created_at_list = []
    updated_at_list = []

    for user in users:
        id_list.append(str(user['id']))
        first_name_list.append(str(user['first_name']))
        last_name_list.append(str(user['last_name']))
        code_melli_list.append(str(user['code_melli']))
        created_at_list.append(str(user['created_at']))
        updated_at_list.append(str(user['updated_at']))
    # TODO: Validation does NOT Work
    if request.method == 'POST':
        # Form NOT validated
        if form.validate() == 0:  # Form is not validated
            return render_template('user_enroll.html', form=form)
        # Form validated correctly
        elif form.validate() != 0:  # Form is validated
            the_id = request.form['id']

            # TODO: (SOLVED) id existence query
            # id_existence_clause = 'ID EXISTS'
            id_existence_clause = db.table('users').where('id', the_id).count()
            # id_existence_clause = db.table('users').where_exists(db.table('users').select(db.raw(1)).where_raw('users.id' == 23))

            # This id exists and the user is ready to be enrolled.
            if id_existence_clause != 0:
                flash('Currently used templates: ' + str(fingerPrint.getTemplateCount()) + ' / ' + str(fingerPrint.getStorageCapacity()))
                our_result['status'] = 1
                # Wait to read the finger
                while fingerPrint.readImage() == 0:
                    pass

                # Converts read image to characteristics and stores it in char buffer 1
                fingerPrint.convertImage(0x01)

                # Checks if finger is already enrolled
                result = fingerPrint.searchTemplate()
                position_number = result[0]

                if position_number >= 0:
                    flash('Template already exists at position #' + str(position_number))
                    our_result['status'] = 2
                    # exit(0)
                    return redirect(url_for('user_enroll'))
                    # TODO: Exits the program and closes the Attendance.py -- should find an alternative

                flash('Remove finger...')
                our_result['status'] = 3
                time.sleep(3)
                flash('Waiting for same finger again...')
                our_result['status'] = 4

                # Wait to read the finger again
                while fingerPrint.readImage() == 0:
                    pass

                # Converts read image to characteristics and stores it in char buffer 2
                fingerPrint.convertImage(0x02)

                # Compares the char buffers
                if fingerPrint.compareCharacteristics() == 0:
                    flash('Fingers do not match')
                    our_result['status'] = 5
                    return redirect(url_for('user_enroll'))
                    # raise Exception('Fingers do not match')

                # Creates a template
                fingerPrint.createTemplate()

                # Saves the template at new position number
                position_number = fingerPrint.storeTemplate()
                flash('Finger enrolled successfully!')
                our_result['status'] = 6
                flash('New template position #' + str(position_number))
                our_result['status'] = 7
                db.table('fingers').insert(user_id=the_id, template_position=position_number)

                flash('This user has been enrolled successfully.')
                our_result['status'] = 8
                return render_template('user_enroll.html',
                                       form=form,
                                       the_id=the_id,
                                       users_table_records_count=users_table_records_count,
                                       id_list=id_list,
                                       first_name_list=first_name_list,
                                       last_name_list=last_name_list,
                                       code_melli_list=code_melli_list,
                                       created_at_list=created_at_list,
                                       updated_at_list=updated_at_list
                                       )
            # This id does not exist.
            elif id_existence_clause == 0:
                flash('Please enter an existing ID number.')
                our_result['status'] = 9
                return render_template('user_enroll.html',
                                       form=form,
                                       the_id=the_id,
                                       users_table_records_count=users_table_records_count,
                                       id_list=id_list,
                                       first_name_list=first_name_list,
                                       last_name_list=last_name_list,
                                       code_melli_list=code_melli_list,
                                       created_at_list=created_at_list,
                                       updated_at_list=updated_at_list
                                       )
    elif request.method == 'GET':
        the_id = None
        return render_template('user_enroll.html',
                               form=form,
                               the_id=the_id,
                               users_table_records_count=users_table_records_count,
                               id_list=id_list,
                               first_name_list=first_name_list,
                               last_name_list=last_name_list,
                               code_melli_list=code_melli_list,
                               created_at_list=created_at_list,
                               updated_at_list=updated_at_list
                               )

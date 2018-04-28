from config import app, publish, store, socket
from flask import render_template, request, flash, redirect, url_for, jsonify
from forms import UserDefineForm, UserEnrollForm, RfidWriteForm
from datetime import datetime
from datetime import timedelta
import hashlib
from orator import DatabaseManager, Model
from pyfingerprint.pyfingerprint import PyFingerprint
from time import time

store['clients'] = []

# Connect to our MySQL database
config = {
    'mysql': {
        'driver': 'mysql',
        'host': 'localhost',
        'database': 'attendance',
        'user': 'jafar',
        'password': '12345678',
        'prefix': ''
    }
}

db = DatabaseManager(config)
Model.set_connection_resolver(db)


class User(Model):
    __table__ = 'users'


class Finger(Model):
    __table__ = 'fingers'


class UserLog(Model):
    __table__ = 'user_logs'


# --------------#
#   Hardware    #
# Initialization#
# --------------#
# Tries to initialize the sensor
f = PyFingerprint('/dev/ttyUSB0', 57600, 0xFFFFFFFF, 0x00000000)


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
    store['clients'].remove(request.sid)


@socket.on('temp')
def temp(data):
    socket.emit('message', str(data), room=request.sid)


# --------------#
#   Endpoints   #
#               #
# --------------#
@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/settings')
def settings():
    return render_template('settings.html')


@app.route('/send')
def send():
    for d in store['clients']:
        publish('message', d)
    return "ok"


# --------------#
#   Settings    #
#   Actions     #
# --------------#
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
                flash('Currently used templates: ' + str(f.getTemplateCount()) + ' / ' + str(f.getStorageCapacity()))
                our_result['status'] = 1
                # Wait to read the finger
                while f.readImage() == 0:
                    pass

                # Converts read image to characteristics and stores it in char buffer 1
                f.convertImage(0x01)

                # Checks if finger is already enrolled
                result = f.searchTemplate()
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
                while f.readImage() == 0:
                    pass

                # Converts read image to characteristics and stores it in char buffer 2
                f.convertImage(0x02)

                # Compares the char buffers
                if f.compareCharacteristics() == 0:
                    flash('Fingers do not match')
                    our_result['status'] = 5
                    return redirect(url_for('user_enroll'))
                    # raise Exception('Fingers do not match')

                # Creates a template
                f.createTemplate()

                # Saves the template at new position number
                position_number = f.storeTemplate()
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


# -------------------------#
#       Daily Routine      #
# -------------------------#
@app.route('/daily_routine', methods=['POST'])
def daily_routine():
    our_result = {'status': 0, 'first_name': '', 'last_name': '', 'last_action': ''}
    # flash('Waiting for finger...')
    # Wait to read the finger
    while f.readImage() == 0:
        pass

    # Converts read image to characteristics and stores it in char buffer 1
    f.convertImage(0x01)

    # Searches template
    result = f.searchTemplate()

    position_number = result[0]
    accuracy_score = result[1]

    # If finger match was NOT found
    if position_number == -1:
        # flash('No match found!')
        our_result['status'] = 2
        # time.sleep(3)
        # exit(0) #TODO: ----
        # return redirect('activate')
        return jsonify(our_result)
    # If finger match was found
    elif position_number != -1:
        # flash('Found template at position #' + str(position_number))
        our_result['status'] = 3
        # flash('The accuracy score is: ' + str(accuracy_score))
        our_result['status'] = 4

        # Executing Queries
        template_position_existence_clause = db.table('fingers').where('template_position', position_number).count()

        # Check if it is the Admin's Finger for going to Settings #TODO: add user role: admin and check it this way
        if position_number == 0:
            # return redirect('activate')
            return redirect('settings')  # TODO: Seems not working
        # Any finger but Admin's
        elif position_number != 0:
            # If the user_id does NOT exist in the fingers table
            if template_position_existence_clause == 0:
                # flash('Finger does NOT exist!')
                our_result['status'] = 5
                # time.sleep(3)
                # return redirect('activate')
                return jsonify(our_result)

            # If the user_id exists in the fingers table
            elif template_position_existence_clause != 0:
                # flash('Finger exists!')
                our_result['status'] = 6
                # Loads the found template to char buffer 1
                f.loadTemplate(position_number, 0x01)

                # Downloads the characteristics of template loaded in char buffer 1
                characterics = str(f.downloadCharacteristics(0x01)).encode('utf-8')

                # Hashes characteristics of template
                # flash('SHA-2 hash of template: ' + hashlib.sha256(characterics).hexdigest())
                our_result['status'] = 7

                the_user_id = db.table('fingers').where('template_position', int(position_number)).pluck('user_id')
                the_first_name = db.table('users').where('id', the_user_id).pluck('first_name')
                the_last_name = db.table('users').where('id', the_user_id).pluck('last_name')
                # Now we have the user_id associated with the template_position
                # flash('The user_id is: ' + str(the_user_id))
                our_result['status'] = 8

                our_result['first_name'] = the_first_name
                our_result['last_name'] = the_last_name
                # print(our_result)

                user_id_existence_clause_2 = db.table('user_logs').where('user_id', the_user_id).order_by('id',
                                                                                                          'desc').pluck(
                    'id')
                # b = cur.execute(
                #     """SELECT * FROM `user_logs` WHERE `user_id`='%d' ORDER BY id DESC LIMIT 1""" % (int(the_user_id)))
                # The user_logs table does NOT have this user_id, inserting the first record of this user_id
                if user_id_existence_clause_2 is None:
                    # flash('The user_logs table does NOT have this user_id. Inserting the record.')
                    the_template_position = position_number
                    the_entered_at = datetime.now()  # time right now
                    the_hash = hashlib.sha256(characterics).hexdigest()
                    the_accuracy = accuracy_score
                    # cur.execute(
                    #     """INSERT INTO `user_logs` (`user_id`, `template_position`, `entered_at`, `hash`, `accuracy`) VALUES ('%d', '%d', '%s', '%s', '%s')"""
                    #     % (int(the_user_id), int(the_template_position), str(the_entered_at), str(the_hash), str(the_accuracy)))
                    db.table('user_logs').insert(user_id=the_user_id, template_position=the_template_position,
                                                 entered_at=the_entered_at, hash=the_hash, accuracy=the_accuracy)

                    our_result['last_action'] = 'You have no records yet.'
                    # time.sleep(3)
                    # return redirect('activate')
                    return jsonify(our_result)


                # The user_logs table has this user_id
                elif user_id_existence_clause_2 is not None:
                    # Retrieve the exited_at associated with the template_position from the fingers table
                    the_exited_at = db.table('user_logs').where('user_id', the_user_id).order_by('id', 'desc').pluck(
                        'exited_at')

                    # exited_at field is NOT empty
                    if the_exited_at is not None:
                        # flash('exited_at field is NOT empty!')
                        our_result['status'] = 10
                        # flash('Inserting NEW record.')
                        our_result['status'] = 11
                        # time.sleep(3)
                        the_template_position = position_number
                        the_entered_at = datetime.now()  # time right now
                        the_hash = hashlib.sha256(characterics).hexdigest()
                        the_accuracy = accuracy_score

                        the_very_last_exited_at = db.table('user_logs').where('user_id', the_user_id).order_by('id',
                                                                                                               'desc').pluck(
                            'exited_at')

                        our_result['last_action'] = the_very_last_exited_at

                        db.table('user_logs').insert(user_id=the_user_id, template_position=the_template_position,
                                                     entered_at=the_entered_at, hash=the_hash, accuracy=the_accuracy)
                        # time.sleep(3)
                        # return redirect('activate')
                        return jsonify(our_result)

                    # exited_at field is empty
                    elif the_exited_at is None:
                        # flash('exited_at field is empty!')
                        our_result['status'] = 12

                        # Retrieve the entered_at associated with the template_position from the fingers table
                        the_very_last_entered_at = db.table('user_logs').where('user_id', the_user_id).order_by('id',
                                                                                                                'desc').pluck(
                            'entered_at')

                        # print(type(the_very_last_entered_at))
                        our_result['status'] = 13
                        temp_time = the_very_last_entered_at + timedelta(seconds=60)  # TODO: Make it a dynamic variable
                        # pprint(temp_time)
                        # flash('temp_time: ' + str(temp_time))
                        the_new_entered_at = datetime.now()  # time right now

                        # More than specified time spent from this finger scan
                        if the_new_entered_at > temp_time:
                            # flash('More than 60 seconds spent from this finger scan!')
                            our_result['status'] = 14
                            # flash('It is a NEW ENTER!')
                            our_result['status'] = 15

                            # time.sleep(3)
                            the_template_position = position_number
                            the_hash = hashlib.sha256(characterics).hexdigest()
                            the_accuracy = accuracy_score

                            our_result[
                                'last_action'] = 'You forgot to attend exit on last time'  # TODO: what should be the last_action if we are in this clause?

                            db.table('user_logs').insert(user_id=the_user_id, template_position=the_template_position,
                                                         entered_at=the_new_entered_at, hash=the_hash,
                                                         accuracy=the_accuracy)
                            # our_result['last_action'] =
                            # time.sleep(3)
                            # return redirect('activate')
                            return jsonify(our_result)

                        # Less than specified times spent from this finger scan
                        else:
                            # flash('Less than 60 seconds spent from this finger scan!')
                            our_result['status'] = 16
                            # flash('It is an EXIT!')
                            our_result['status'] = 17
                            # time.sleep(3)
                            the_exited_at = datetime.now()  # time right now

                            db.table('user_logs').where('entered_at', the_very_last_entered_at).update(
                                exited_at=the_exited_at)

                            our_result['last_action'] = the_very_last_entered_at
                            # time.sleep(3)
                            # return redirect('activate')
                            return jsonify(our_result)


# -------------------------#
#       RFID Write         #
# -------------------------#
@app.route('/rfid_write', methods=['POST', 'GET'])
def rfid_write():
    form = RfidWriteForm()  # TODO: Reconsider this

    if request.method == 'POST':
        the_id = request.form['id']


# -------------------------#
#       RFID Read          #
# -------------------------#
@app.route('/rfid_read', methods=['POST', 'GET'])
def rfid_read():
    pass  # TODO: Didn't work on it

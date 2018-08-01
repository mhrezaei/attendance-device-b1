from time import sleep, time, strftime, localtime
from datetime import datetime, timedelta
import urllib2
import urllib
import schedule
from serial import SerialException
from config import store, socket, publish, fingerprint, db, User, UserLog, api_token
import hashlib
from global_variables import working_hours
from global_variables import attendance_not_allowed_timeout
from global_variables import handle_the_is_synced_field_period
from global_variables import request_to_refresh_for_crud_on_laravel_period
from global_variables import sync_users_period
from global_variables import maximum_allowed_fingers_for_usual_users
from global_variables import maximum_allowed_fingers_for_admin_users
from global_variables import device_template_position_except_fingerprint
from global_variables import device_hash_except_fingerprint
from global_variables import device_accuracy_except_fingerprint
from global_variables import rfid_unique_id_except_rfid
import RPi.GPIO as GPIO
import SimpleMFRC522
import os
import spi
import json
import bluetooth

store['fingerPrintEnabled'] = False
store['rfidEnabled'] = False


# def trigger_relay_on_enter():
#     try:
#         print('\n\n***trigger_relay_on_enter***----' + strftime('%Y-%m-%d %H:%M:%S', localtime(time())) + '\n\n')
#         relay_s_pin = 17  # GPIO 17 -- Pin 11 -- relay
#         GPIO.setmode(GPIO.BCM)  # Numbers GPIOs by physical location
#         GPIO.setup(relay_s_pin, GPIO.OUT)  # Set relay_s_pin's mode to output
#         GPIO.output(relay_s_pin, GPIO.HIGH)
#         sleep(2)
#         GPIO.output(relay_s_pin, GPIO.LOW)
#
#     except KeyboardInterrupt:
#         print(' * Terminating... ')
#         os.system('kill -9 %d' % os.getpid())
#
#     except Exception as e:
#         error_template = "An exception of type {0} occurred. Arguments:\n{1!r}"
#         error_message = error_template.format(type(e).__name__, e.args)
#         print('\n\n' + error_message + '\n\n')
#
#     finally:
#         GPIO.cleanup()


def receive(action, message):
    if action == 'fingerPrintStatus':
        print(message)
        socket.emit('fingerPrintStatus', message, broadcast=True)
    pass


def send_actual_attend_to_laravel(
        sending_is_synced,
        sending_user_id,
        sending_effected_at,
        sending_type,
        sending_device,
        sending_device_template_position,
        sending_device_hash,
        sending_device_accuracy,
        sending_rfid_unique_id
):
    try:
        print('\n\n***send_actual_attend_to_laravel***----' + strftime('%Y-%m-%d %H:%M:%S', localtime(time())) + '\n\n')
        url = 'http://yasna.local/attendance/api/v1/users/attends'  # @TODO: Must be dynamic later.

        # Prepare the data
        query_args = {
            'is_synced': int(sending_is_synced),
            'user_id': int(sending_user_id),
            'effected_at': str(sending_effected_at),
            'type': str(sending_type),
            'device': str(sending_device),
            'device_template_position': int(sending_device_template_position),
            'device_hash': str(sending_device_hash),
            'device_accuracy': int(sending_device_accuracy),
            'rfid_unique_id': str(sending_rfid_unique_id),
        }

        header = {"Accept": "application/json",
                  "Authorization": '760483978406f1195959ef81a90c91ef'
                  }  # @TODO: Ask - Must be dynamic later? How?

        data = urllib.urlencode(query_args)

        # Send HTTP POST request
        request = urllib2.Request(url, data, header)

        # Sends the request and catches the response
        response = urllib2.urlopen(request)

        # Extracts the response
        html = response.read()

        print(html)

    except KeyboardInterrupt:
        print(' * Terminating... ')
        os.system('kill -9 %d' % os.getpid())

    except Exception as e:
        error_template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        error_message = error_template.format(type(e).__name__, e.args)
        print('\n\n' + error_message + '\n\n')


def handle_the_is_synced_field():
    try:
        print('\n\n***handle_the_is_synced_field***----' + strftime('%Y-%m-%d %H:%M:%S', localtime(time())) + '\n\n')
        remained_is_synced_0 = UserLog.where('is_synced', 0).get()

        for is_synced_0 in remained_is_synced_0:
            send_actual_attend_to_laravel(
                int(1),
                int(is_synced_0.user_id),
                str(is_synced_0.effected_at),
                str(is_synced_0.type),
                str(is_synced_0.device),
                int(is_synced_0.template_position),
                str(is_synced_0.hash),
                int(is_synced_0.accuracy),
                str(is_synced_0.rfid_unique_id)
            )
            is_synced_0.update(is_synced=1)
            print('\n\nSent one row of is_synced=0\n\n')

        print('------Nothing left to sync------' + strftime('%Y-%m-%d %H:%M:%S', localtime(time())) + '\n\n')

    except KeyboardInterrupt:
        print(' * Terminating... ')
        os.system('kill -9 %d' % os.getpid())

    except urllib2.HTTPError as e:  # @TODO: Ask - Right?
        print('/\/\/\/\/\/\/\/\ HTTPError happened: ' + str(e.code))

    except Exception as e:
        error_template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        error_message = error_template.format(type(e).__name__, e.args)
        print('\n\n' + error_message + '\n\n')


def run_fingerprint():
    schedule.run_pending()
    if store['fingerPrintEnabled']:  # boolean
        # sleep(0.5) #TODO: 1 second or not
        our_result = {'status': 0, 'first_name': '', 'last_name': '', 'last_action': ''}
        the_is_synced = 0
        the_device = 'fingerprint'

        # read_image = None
        try:
            read_image = fingerprint.readImage()
            if read_image != 0:
                finger_read_time = int(time())

                fingerprint.convertImage(0x01)
                # Searches template
                result = fingerprint.searchTemplate()

                position_number = result[0]
                accuracy_score = result[1]

                # If finger match was NOT found
                if position_number == -1:
                    # flash('No match found!')
                    our_result['status'] = 1000
                    publish('fingerPrintStatus', our_result)

                # If finger match was found
                if position_number != -1:
                    print('Found Template')
                    fingerprint.loadTemplate(position_number, 0x01)
                    characterics = str(fingerprint.downloadCharacteristics(0x01)).encode('utf-8')

                    user_related_with_this_finger = db.table('fingers').where('template_position',
                                                                              position_number).pluck('user_id')
                    is_active_clause = db.table('users').where('id', user_related_with_this_finger).pluck('is_active')

                    if is_active_clause == 0:  # This user is NOT active
                        our_result['status'] = 1001
                        publish('fingerPrintStatus', our_result)
                        sleep(2)

                    elif is_active_clause != 0:  # This user is active

                        user_related_with_this_finger = db.table('fingers').where('template_position',
                                                                                  position_number).pluck('user_id')
                        this_user_last_effect = db.table('user_logs').where('user_id',
                                                                            user_related_with_this_finger).order_by(
                            'id', 'desc').pluck('effected_at')

                        if this_user_last_effect is None:  # This user has no records in the table yet. It's a fresh record.
                            the_user_id = user_related_with_this_finger
                            the_effected_at = datetime.now()
                            the_type = 'normal_in'  # @TODO: Must be dynamic later.
                            the_template_position = position_number
                            the_hash = hashlib.sha256(characterics).hexdigest()
                            the_accuracy = accuracy_score

                            the_first_name = db.table('users').where('id', user_related_with_this_finger).pluck(
                                'first_name')
                            the_last_name = db.table('users').where('id', user_related_with_this_finger).pluck(
                                'last_name')

                            our_result['first_name'] = the_first_name
                            our_result['last_name'] = the_last_name
                            our_result['last_action'] = 'None'

                            # trigger_relay_on_enter()

                            db.table('user_logs').insert(is_synced=the_is_synced,
                                                         user_id=the_user_id,
                                                         effected_at=the_effected_at,
                                                         type=the_type,
                                                         device=the_device,
                                                         template_position=the_template_position,
                                                         hash=the_hash,
                                                         accuracy=the_accuracy,
                                                         rfid_unique_id=str(rfid_unique_id_except_rfid)
                                                         )

                            our_result['status'] = 1002
                            publish('fingerPrintStatus',
                                    our_result)  # @TODO: Don't forget to set a fresh status right after 'if' and update wiki.
                            sleep(2)

                        if this_user_last_effect is not None:  # This user already has a record in the table.
                            last_effect_type = db.table('user_logs').where('user_id',
                                                                           user_related_with_this_finger).order_by('id',
                                                                                                                   'desc').pluck(
                                'type')

                            if last_effect_type == 'normal_in':
                                this_user_last_attendance_action = int(
                                    this_user_last_effect.strftime('%s'))  # Converted to epoch
                                check_time = int(this_user_last_attendance_action + attendance_not_allowed_timeout)

                                if finger_read_time < check_time:  # attendance_not_allowed_timeout has NOT passed. NOT ready to apply user log.
                                    # flash('attendance_not_allowed_timeout has NOT passed.')
                                    # print('STATUS 18 - NOT allowed to apply user log.')
                                    our_result['status'] = 1003
                                    publish('fingerPrintStatus', our_result)
                                    sleep(2)

                                elif finger_read_time >= check_time:  # attendance_not_allowed_timeout has passed. Ready to apply user log.
                                    # print('STATUS 19 - Allowed to apply user log.')
                                    the_first_name = db.table('users').where('id', user_related_with_this_finger).pluck(
                                        'first_name')
                                    the_last_name = db.table('users').where('id', user_related_with_this_finger).pluck(
                                        'last_name')

                                    the_very_last_normal_in_effected_at = db.table('user_logs').where('user_id',
                                                                                                      user_related_with_this_finger).where(
                                        'type', 'normal_in').order_by('id', 'desc').pluck('effected_at')

                                    # the_very_last_normal_in_effected_at_epoch = int(the_very_last_normal_in_effected_at.strftime('%s'))  # Converted to epoch

                                    check_working_hours_time = the_very_last_normal_in_effected_at + timedelta(
                                        seconds=working_hours)

                                    the_new_effected_at = datetime.now()  # time right now

                                    # More than specified time spent from this finger scan
                                    if the_new_effected_at > check_working_hours_time:
                                        our_result['first_name'] = the_first_name
                                        our_result['last_name'] = the_last_name
                                        our_result['last_action'] = str(the_very_last_normal_in_effected_at)

                                        the_user_id = user_related_with_this_finger
                                        the_effected_at = the_new_effected_at
                                        the_type = 'normal_in'
                                        the_template_position = position_number
                                        the_hash = hashlib.sha256(characterics).hexdigest()
                                        the_accuracy = accuracy_score

                                        # trigger_relay_on_enter()

                                        db.table('user_logs').insert(is_synced=the_is_synced,
                                                                     user_id=the_user_id,
                                                                     effected_at=the_effected_at,
                                                                     type=the_type,
                                                                     device=the_device,
                                                                     template_position=the_template_position,
                                                                     hash=the_hash,
                                                                     accuracy=the_accuracy,
                                                                     rfid_unique_id=str(rfid_unique_id_except_rfid)
                                                                     )
                                        our_result['status'] = 1004
                                        publish('fingerPrintStatus',
                                                our_result)  # @TODO: Don't forget to set a fresh status right after 'if' and update wiki.
                                        sleep(2)

                                    elif the_new_effected_at <= check_working_hours_time:
                                        our_result['first_name'] = the_first_name
                                        our_result['last_name'] = the_last_name
                                        our_result['last_action'] = str(the_very_last_normal_in_effected_at)

                                        the_user_id = user_related_with_this_finger
                                        the_effected_at = datetime.now()
                                        the_type = 'normal_out'  # @TODO: Must be dynamic later.
                                        the_template_position = position_number
                                        the_hash = hashlib.sha256(characterics).hexdigest()
                                        the_accuracy = accuracy_score

                                        db.table('user_logs').insert(is_synced=the_is_synced,
                                                                     user_id=the_user_id,
                                                                     effected_at=the_effected_at,
                                                                     type=the_type,
                                                                     device=the_device,
                                                                     template_position=the_template_position,
                                                                     hash=the_hash,
                                                                     accuracy=the_accuracy,
                                                                     rfid_unique_id=str(rfid_unique_id_except_rfid)
                                                                     )
                                        our_result['status'] = 1005
                                        publish('fingerPrintStatus',
                                                our_result)  # @TODO: Don't forget to set a fresh status right after 'if' and update wiki.
                                        sleep(2)

                            elif last_effect_type == 'normal_out':
                                this_user_last_attendance_action = int(
                                    this_user_last_effect.strftime('%s'))  # Converted to epoch
                                check_time = int(this_user_last_attendance_action + attendance_not_allowed_timeout)

                                the_very_last_normal_in_effected_at = db.table('user_logs').where('user_id',
                                                                                                  user_related_with_this_finger).where(
                                    'type', 'normal_in').order_by('id', 'desc').pluck('effected_at')

                                if finger_read_time < check_time:  # attendance_not_allowed_timeout has NOT passed. NOT ready to apply user log.
                                    # flash('attendance_not_allowed_timeout has NOT passed.')
                                    # print('STATUS 18 - NOT allowed to apply user log.')
                                    our_result['status'] = 1006
                                    publish('fingerPrintStatus',
                                            our_result)  # @TODO: Don't forget to set a fresh status right after 'if' and update wiki.
                                    sleep(2)

                                elif finger_read_time >= check_time:  # attendance_not_allowed_timeout has passed. Ready to apply user log.
                                    # print('STATUS 19 - Allowed to apply user log.')
                                    the_first_name = db.table('users').where('id', user_related_with_this_finger).pluck(
                                        'first_name')
                                    the_last_name = db.table('users').where('id', user_related_with_this_finger).pluck(
                                        'last_name')
                                    # Now we have the user_id associated with the template_position
                                    # flash('The user_id is: ' + str(the_user_id))

                                    our_result['first_name'] = the_first_name
                                    our_result['last_name'] = the_last_name
                                    our_result['last_action'] = str(the_very_last_normal_in_effected_at)

                                    the_user_id = user_related_with_this_finger
                                    the_effected_at = datetime.now()
                                    the_type = 'normal_in'  # @TODO: Must be dynamic later.
                                    the_template_position = position_number
                                    the_hash = hashlib.sha256(characterics).hexdigest()
                                    the_accuracy = accuracy_score

                                    # trigger_relay_on_enter()

                                    db.table('user_logs').insert(is_synced=the_is_synced,
                                                                 user_id=the_user_id,
                                                                 effected_at=the_effected_at,
                                                                 type=the_type,
                                                                 device=the_device,
                                                                 template_position=the_template_position,
                                                                 hash=the_hash,
                                                                 accuracy=the_accuracy,
                                                                 rfid_unique_id=str(rfid_unique_id_except_rfid)
                                                                 )

                                    our_result['status'] = 1007
                                    publish('fingerPrintStatus',
                                            our_result)  # @TODO: Don't forget to set a fresh status right after 'if' and update wiki.
                                    sleep(2)

        except KeyboardInterrupt:
            print(' * Terminating... ')
            os.system('kill -9 %d' % os.getpid())

        except SerialException:
            print('Serial Exception happened.')

        except Exception as e:
            error_template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            error_message = error_template.format(type(e).__name__, e.args)
            print('\n\n' + error_message + '\n\n')

    else:
        sleep(1)


def run_rfid():
    if store['rfidEnabled']:  # boolean
        our_result = dict()
        our_result['status'] = 30
        our_result['message'] = 'Nothing done yet.'
        sleep(1)
        reader = SimpleMFRC522.SimpleMFRC522()
        the_is_synced = 0
        the_device = 'rfid'

        try:
            unique_id, rfid_owner_user_id = reader.read_no_block()

            if unique_id is not None:  # Detected RFID card.
                print('RFID is read.')
                rfid_read_time = time()
                unique_id = str(unique_id)
                print(unique_id)
                print(rfid_owner_user_id)

                unique_id_existence_clause = db.table('rfid_cards').where('unique_id', unique_id).count()

                if unique_id_existence_clause:  # This RFID card is registered in the rfid_cards table.

                    user_related_with_this_rfid_card = db.table('rfid_cards').where('unique_id', unique_id).pluck(
                        'user_id')

                    the_first_name = db.table('users').where('id', user_related_with_this_rfid_card).pluck('first_name')
                    the_last_name = db.table('users').where('id', user_related_with_this_rfid_card).pluck('last_name')
                    is_active_clause = db.table('users').where('id', user_related_with_this_rfid_card).pluck(
                        'is_active')

                    if is_active_clause == 0:  # This user is NOT active anymore.
                        our_result['status'] = 2001
                        # flash('This user is not active anymore.')
                        publish('fingerPrintStatus', our_result)

                    elif is_active_clause != 0:  # This user is active.

                        this_user_last_effect = db.table('user_logs').where('user_id',
                                                                            user_related_with_this_rfid_card).order_by(
                            'id', 'desc').pluck('effected_at')

                        if this_user_last_effect is None:  # This user has no records in the table yet. It's a fresh record.
                            the_user_id = user_related_with_this_rfid_card
                            the_effected_at = datetime.now()
                            the_type = 'normal_in'  # @TODO: Must be dynamic later.
                            the_rfid_unique_id = unique_id

                            our_result['first_name'] = the_first_name
                            our_result['last_name'] = the_last_name
                            our_result['last_action'] = 'None'

                            # trigger_relay_on_enter()

                            db.table('user_logs').insert(is_synced=the_is_synced,
                                                         user_id=the_user_id,
                                                         effected_at=the_effected_at,
                                                         type=the_type,
                                                         device=the_device,
                                                         template_position=int(
                                                             device_template_position_except_fingerprint),
                                                         hash=str(device_hash_except_fingerprint),
                                                         accuracy=int(device_accuracy_except_fingerprint),
                                                         rfid_unique_id=str(the_rfid_unique_id))

                            our_result['status'] = 2002
                            publish('fingerPrintStatus',
                                    our_result)  # @TODO: Don't forget to set a fresh status right after 'if' and update wiki.
                            sleep(2)

                        if this_user_last_effect is not None:  # This user already has a record in the table.
                            last_effect_type = db.table('user_logs').where('user_id',
                                                                           user_related_with_this_rfid_card).order_by(
                                'id', 'desc').pluck('type')

                            if last_effect_type == 'normal_in':
                                this_user_last_attendance_action = int(
                                    this_user_last_effect.strftime('%s'))  # Converted to epoch
                                check_time = int(this_user_last_attendance_action + attendance_not_allowed_timeout)

                                if rfid_read_time < check_time:  # attendance_not_allowed_timeout has NOT passed. NOT ready to apply user log.
                                    # flash('attendance_not_allowed_timeout has NOT passed.')
                                    # print('STATUS 18 - NOT allowed to apply user log.')
                                    our_result['status'] = 2003
                                    publish('fingerPrintStatus', our_result)
                                    sleep(2)

                                elif rfid_read_time >= check_time:  # attendance_not_allowed_timeout has passed. Ready to apply user log.
                                    # print('STATUS 19 - Allowed to apply user log.')
                                    the_first_name = db.table('users').where('id',
                                                                             user_related_with_this_rfid_card).pluck(
                                        'first_name')
                                    the_last_name = db.table('users').where('id',
                                                                            user_related_with_this_rfid_card).pluck(
                                        'last_name')

                                    the_very_last_normal_in_effected_at = db.table('user_logs').where('user_id',
                                                                                                      user_related_with_this_rfid_card).where(
                                        'type', 'normal_in').order_by('id', 'desc').pluck('effected_at')

                                    # the_very_last_normal_in_effected_at_epoch = int(the_very_last_normal_in_effected_at.strftime('%s'))  # Converted to epoch

                                    check_working_hours_time = the_very_last_normal_in_effected_at + timedelta(
                                        seconds=working_hours)

                                    the_new_effected_at = datetime.now()  # time right now

                                    # More than specified time spent from this finger scan
                                    if the_new_effected_at > check_working_hours_time:
                                        our_result['first_name'] = the_first_name
                                        our_result['last_name'] = the_last_name
                                        our_result['last_action'] = str(the_very_last_normal_in_effected_at)

                                        the_user_id = user_related_with_this_rfid_card
                                        the_effected_at = the_new_effected_at
                                        the_type = 'normal_in'
                                        the_rfid_unique_id = unique_id

                                        # trigger_relay_on_enter()

                                        db.table('user_logs').insert(is_synced=the_is_synced,
                                                                     user_id=the_user_id,
                                                                     effected_at=the_effected_at,
                                                                     type=the_type,
                                                                     device=the_device,
                                                                     template_position=int(
                                                                         device_template_position_except_fingerprint),
                                                                     hash=str(device_hash_except_fingerprint),
                                                                     accuracy=int(device_accuracy_except_fingerprint),
                                                                     rfid_unique_id=str(the_rfid_unique_id))
                                        our_result['status'] = 2004
                                        publish('fingerPrintStatus',
                                                our_result)  # @TODO: Don't forget to set a fresh status right after 'if' and update wiki.
                                        sleep(2)

                                    elif the_new_effected_at <= check_working_hours_time:
                                        our_result['first_name'] = the_first_name
                                        our_result['last_name'] = the_last_name
                                        our_result['last_action'] = str(the_very_last_normal_in_effected_at)

                                        the_user_id = user_related_with_this_rfid_card
                                        the_effected_at = datetime.now()
                                        the_type = 'normal_out'  # @TODO: Must be dynamic later.
                                        the_rfid_unique_id = unique_id

                                        db.table('user_logs').insert(is_synced=the_is_synced,
                                                                     user_id=the_user_id,
                                                                     effected_at=the_effected_at,
                                                                     type=the_type,
                                                                     device=the_device,
                                                                     template_position=int(
                                                                         device_template_position_except_fingerprint),
                                                                     hash=str(device_hash_except_fingerprint),
                                                                     accuracy=int(device_accuracy_except_fingerprint),
                                                                     rfid_unique_id=str(the_rfid_unique_id))
                                        our_result['status'] = 2005
                                        publish('fingerPrintStatus',
                                                our_result)  # @TODO: Don't forget to set a fresh status right after 'if' and update wiki.
                                        sleep(2)

                            elif last_effect_type == 'normal_out':
                                this_user_last_attendance_action = int(
                                    this_user_last_effect.strftime('%s'))  # Converted to epoch
                                check_time = int(this_user_last_attendance_action + attendance_not_allowed_timeout)

                                the_very_last_normal_in_effected_at = db.table('user_logs').where('user_id',
                                                                                                  user_related_with_this_rfid_card).where(
                                    'type', 'normal_in').order_by('id', 'desc').pluck('effected_at')

                                if rfid_read_time < check_time:  # attendance_not_allowed_timeout has NOT passed. NOT ready to apply user log.
                                    # flash('attendance_not_allowed_timeout has NOT passed.')
                                    # print('STATUS 18 - NOT allowed to apply user log.')
                                    our_result['status'] = 2006
                                    publish('fingerPrintStatus',
                                            our_result)  # @TODO: Don't forget to set a fresh status right after 'if' and update wiki.
                                    sleep(2)

                                elif rfid_read_time >= check_time:  # attendance_not_allowed_timeout has passed. Ready to apply user log.
                                    # print('STATUS 19 - Allowed to apply user log.')
                                    the_first_name = db.table('users').where('id',
                                                                             user_related_with_this_rfid_card).pluck(
                                        'first_name')
                                    the_last_name = db.table('users').where('id',
                                                                            user_related_with_this_rfid_card).pluck(
                                        'last_name')
                                    # Now we have the user_id associated with the template_position
                                    # flash('The user_id is: ' + str(the_user_id))

                                    our_result['first_name'] = the_first_name
                                    our_result['last_name'] = the_last_name
                                    our_result['last_action'] = str(the_very_last_normal_in_effected_at)

                                    the_user_id = user_related_with_this_rfid_card
                                    the_effected_at = datetime.now()
                                    the_type = 'normal_in'  # @TODO: Must be dynamic later.
                                    the_rfid_unique_id = unique_id

                                    # trigger_relay_on_enter()

                                    db.table('user_logs').insert(is_synced=the_is_synced,
                                                                 user_id=the_user_id,
                                                                 effected_at=the_effected_at,
                                                                 type=the_type,
                                                                 device=the_device,
                                                                 template_position=int(
                                                                     device_template_position_except_fingerprint),
                                                                 hash=str(device_hash_except_fingerprint),
                                                                 accuracy=int(device_accuracy_except_fingerprint),
                                                                 rfid_unique_id=str(the_rfid_unique_id))
                                    our_result['status'] = 2007
                                    publish('fingerPrintStatus',
                                            our_result)  # @TODO: Don't forget to set a fresh status right after 'if' and update wiki.
                                    sleep(2)

                else:  # This RFID card is NOT registered in the rfid_cards table.
                    our_result['status'] = 2000
                    # flash('This RFID card is not registered.')
                    publish('fingerPrintStatus', our_result)

        except KeyboardInterrupt:
            print(' * Terminating... ')
            os.system('kill -9 %d' % os.getpid())

        except Exception as e:
            error_template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            error_message = error_template.format(type(e).__name__, e.args)
            print('\n\n' + error_message + '\n\n')

        finally:
            GPIO.cleanup()
            spi.closeSPI()

    else:
        sleep(1)


def send_synced_id_list_to_laravel(the_id_list):
    try:
        print('\n\n***send_synced_id_list_to_laravel***----' + strftime('%Y-%m-%d %H:%M:%S', localtime(time())) + '\n\n')
        url = 'http://yasna.local/attendance/api/v1/updates/is_synceds'  # @TODO: Must be dynamic later.

        # Prepare the data
        query_args = {
            'id_list': the_id_list
        }

        header = {
            "Accept": "application/json",
            "Authorization": '760483978406f1195959ef81a90c91ef'}  # @TODO: Must be dynamic later.

        data = urllib.urlencode(query_args)

        # Send HTTP POST request
        request = urllib2.Request(url, data, header)

        # Sends the request and catches the response
        response = urllib2.urlopen(request)

        # Extracts the response
        html = response.read()

        # print(html)
        parsed = json.loads(html)

        http_status = 'Not set yet.'

        for key, value in parsed.items():
            if key == 'status':
                http_status = value

        print('\n\nHttp status was: ' + str(http_status) + '\n\n')

        if http_status == 200:
            for key, value in parsed.items():
                if key == 'results':
                    # first_character_removed = value.replace('[', '')
                    # final_desired_string = first_character_removed.replace(']', '')
                    # print(final_desired_string)
                    print(value)

        else:
            print('\n\nHttp status was not 200.\n\n')

        # else:  # @TODO: Else if status != 200

    except KeyboardInterrupt:
        print(' * Terminating... ')
        os.system('kill -9 %d' % os.getpid())

    except urllib2.HTTPError as e:  # @TODO: Ask - Right?
        print('\n\n/\/\/\/\/\/\/\/\ HTTPError happened: ' + str(e.code) + '\n\n')

    except Exception as e:
        error_template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        error_message = error_template.format(type(e).__name__, e.args)
        print('\n\n' + error_message + '\n\n')


def request_to_refresh_for_crud_on_laravel():
    try:
        print('\n\n***request_to_refresh_for_crud_on_laravel***----' + strftime('%Y-%m-%d %H:%M:%S', localtime(time())) + '\n\n')
        url = 'http://yasna.local/attendance/api/v1/syncs/cruds'  # @TODO: Must be dynamic later.

        # Prepare the data
        query_args = {}

        header = {
            "Accept": "application/json",
            "Authorization": '760483978406f1195959ef81a90c91ef'}  # @TODO: Must be dynamic later.

        data = urllib.urlencode(query_args)

        # Send HTTP POST request
        request = urllib2.Request(url, data, header)

        # Sends the request and catches the response
        response = urllib2.urlopen(request)

        # Extracts the response
        html = response.read()

        # print(html)

        parsed = json.loads(html)

        http_status = 'Not set yet.'

        for key, value in parsed.items():
            if key == 'status':
                http_status = value

        print('\n\nHttp status was: ' + str(http_status) + '\n\n')

        synced_id_list = []

        if http_status == 200:
            for key, value in parsed.items():
                if key == 'results':
                    for i in range(0, len(value)):
                        UserLog.insert(
                            is_synced=1,
                            user_id=int(value[i]['user_id']),
                            effected_at=str(value[i]['effected_at']),
                            type=str(value[i]['type']),
                            device=str(value[i]['device']),
                            template_position=int(value[i]['device_template_position']),
                            hash=str(value[i]['device_hash']),
                            accuracy=int(value[i]['device_accuracy']),
                            rfid_unique_id=str(value[i]['rfid_unique_id']),
                        )
                        synced_id_list.insert(0, value[i]['id'])

            send_synced_id_list_to_laravel(str(synced_id_list))

        else:
            print('\n\nHttp status was not 200.\n\n')

        # else:  # @TODO: Else if status != 200

    except KeyboardInterrupt:
        print(' * Terminating... ')
        os.system('kill -9 %d' % os.getpid())

    except urllib2.HTTPError as e:  # @TODO: Ask - Right?
        print('/\/\/\/\/\/\/\/\ HTTPError happened: ' + str(e.code))

    except Exception as e:
        error_template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        error_message = error_template.format(type(e).__name__, e.args)
        print('\n\n' + error_message + '\n\n')


def unmatched_values_list(list1, list2):
    return list(set(list1) - set(list2))


def sync_users():
    try:
        print('\n\n***sync_users***----' + strftime('%Y-%m-%d %H:%M:%S', localtime(time())) + '\n\n')
        url = 'http://yasna.local/attendance/api/v1/users/lists'  # @TODO: Must be dynamic later.

        # Prepare the data
        query_args = {}

        header = {
            "Accept": "application/json",
            "Authorization": '760483978406f1195959ef81a90c91ef'}  # @TODO: Must be dynamic later.

        data = urllib.urlencode(query_args)

        # Send HTTP POST request
        request = urllib2.Request(url, data, header)

        # print(request)

        # Sends the request and catches the response
        response = urllib2.urlopen(request)

        # print(response)

        # Extracts the response
        html = response.read()

        # print(html)
        parsed = json.loads(html)

        code_mellis_list_in_attendance_machine = list(User.get().pluck('code_melli'))
        code_mellis_list_sent_from_laravel = []

        http_status = 'Not set yet.'

        for key, value in parsed.items():
            if key == 'status':
                http_status = value

        print('\n\nHttp status was: ' + str(http_status) + '\n\n')

        if http_status == 200:
            for key, value in parsed.items():
                if key == 'results':
                    for i in range(0, len(value['users'])):
                        code_mellis_list_sent_from_laravel.insert(0, value['users'][i]['code_melli'])
                        code_melli_existence_clause = User.where('code_melli', value['users'][i]['code_melli']).count()
                        if not code_melli_existence_clause:  # This code_melli does not exist. Insert it.
                            User.insert(
                                user_name=str(value['users'][i]['email']),
                                first_name=value['users'][i]['name_first'],
                                last_name=value['users'][i]['name_last'],
                                code_melli=str(value['users'][i]['code_melli']),
                                is_admin=0,
                                maximum_allowed_fingers=maximum_allowed_fingers_for_usual_users,
                                recorded_fingers_count=0,
                                is_active=1,
                            )
                            print('Inserted a new user.')

                            if 'is_admin' in value['users'][i].keys():
                                if value['users'][i]['is_admin'] == 1:
                                    User.where('code_melli', str(value['users'][i]['code_melli'])).update(
                                        is_admin=1,
                                        maximum_allowed_fingers=maximum_allowed_fingers_for_admin_users,
                                    )
                                    print('Updated the user to an admin.')

                    for code_melli in unmatched_values_list(code_mellis_list_in_attendance_machine,
                                                            code_mellis_list_sent_from_laravel):
                        User.where('code_melli', str(code_melli)).update(is_active=0)
                        print('One user is inactive.')

                    print('Done with syncing users.')

        else:
            print('\n\nHttp status was not 200.\n\n')

    except KeyboardInterrupt:
        print(' * Terminating... ')
        os.system('kill -9 %d' % os.getpid())

    except urllib2.HTTPError as e:  # @TODO: Ask - Right?
        print('/\/\/\/\/\/\/\/\ HTTPError happened: ' + str(e.code))

    except Exception as e:
        error_template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        error_message = error_template.format(type(e).__name__, e.args)
        print('\n\n' + error_message + '\n\n')


# def look_up_nearby_bluetooth_devices():
#     try:
#         print('\n\n***look_up_nearby_bluetooth_devices***----' + strftime('%Y-%m-%d %H:%M:%S', localtime(time())) + '\n\n')
#         bdaddr_list = []
#         nearby_devices = bluetooth.discover_devices()
#         for bdaddr in nearby_devices:
#             bdaddr_list.insert(0, bdaddr)
#             if bdaddr in bdaddr_list:
#                 print('Detected\t' + str(bluetooth.lookup_name(bdaddr)) + '\t' + " [" + str(bdaddr) + "]")
#
#     except Exception as e:
#         error_template = "An exception of type {0} occurred. Arguments:\n{1!r}"
#         error_message = error_template.format(type(e).__name__, e.args)
#         print('\n\n' + error_message + '\n\n')


schedule.every(handle_the_is_synced_field_period).seconds.do(handle_the_is_synced_field)
schedule.every(request_to_refresh_for_crud_on_laravel_period).seconds.do(request_to_refresh_for_crud_on_laravel)
schedule.every(sync_users_period).seconds.do(sync_users)
# schedule.every(1).seconds.do(look_up_nearby_bluetooth_devices)

from time import sleep, time, strftime, localtime
from datetime import datetime, timedelta
import urllib2
import urllib
import schedule
from serial import SerialException

from config import store, socket, publish, fingerprint, db, User, UserLog, api_token
import hashlib
from globla_variables import working_hours
from globla_variables import attendance_not_allowed_timeout
from globla_variables import handle_the_is_synced_field_period
import RPi.GPIO as GPIO
import SimpleMFRC522
import os
import spi

store['fingerPrintEnabled'] = False
store['rfidEnabled'] = False


def trigger_relay_on_enter():
    relay_pin = 11  # Pin 11 -- GPIO 17 -- relay
    GPIO.setmode(GPIO.BOARD)  # Numbers GPIOs by physical location
    GPIO.setup(relay_pin, GPIO.OUT)  # Set relay_pin's mode to output
    GPIO.output(relay_pin, GPIO.HIGH)
    sleep(2)
    GPIO.output(relay_pin, GPIO.LOW)


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

    except Exception as e:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(e).__name__, e.args)
        print(message)


def handle_the_is_synced_field():
    remained_is_synced_0 = UserLog.where('is_synced', 0).get()

    for is_synced_0 in remained_is_synced_0:
        # is_synced_0.update(is_synced=1)
        # print(is_synced_0.user_id)
        # print(is_synced_0.effected_at)
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
        # print('record: ' + str(is_synced_0.id) + " is synced now.")
        print('Sent one row of is_synced=0')

    print('------Nothing left to sync------' + strftime('%Y-%m-%d %H:%M:%S', localtime(time())))


def run_fingerprint():
    schedule.run_pending()
    if store['fingerPrintEnabled']:  # boolean
        # sleep(0.5) #TODO: 1 second or not
        our_result = {'status': 0, 'first_name': '', 'last_name': '', 'last_action': ''}
        the_is_synced = 0
        the_device = 'fingerprint'
        the_rfid_unique_id = 0

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

                            trigger_relay_on_enter()
                            db.table('user_logs').insert(is_synced=the_is_synced,
                                                         user_id=the_user_id,
                                                         effected_at=the_effected_at,
                                                         type=the_type,
                                                         device=the_device,
                                                         template_position=the_template_position,
                                                         hash=the_hash,
                                                         accuracy=the_accuracy)

                            # Uncomment for real-time attend to laravel
                            # send_actual_attend_to_laravel(the_is_synced,
                            #                               the_user_id,
                            #                               the_effected_at,
                            #                               the_type,
                            #                               the_device,
                            #                               the_template_position,
                            #                               the_hash,
                            #                               the_accuracy,
                            #                               the_rfid_unique_id)

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

                                        trigger_relay_on_enter()

                                        db.table('user_logs').insert(is_synced=the_is_synced,
                                                                     user_id=the_user_id,
                                                                     effected_at=the_effected_at,
                                                                     type=the_type,
                                                                     device=the_device,
                                                                     template_position=the_template_position,
                                                                     hash=the_hash,
                                                                     accuracy=the_accuracy)
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
                                                                     accuracy=the_accuracy)
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

                                    trigger_relay_on_enter()

                                    db.table('user_logs').insert(is_synced=the_is_synced,
                                                                 user_id=the_user_id,
                                                                 effected_at=the_effected_at,
                                                                 type=the_type,
                                                                 device=the_device,
                                                                 template_position=the_template_position,
                                                                 hash=the_hash,
                                                                 accuracy=the_accuracy)

                                    # Uncomment for real-time attend to laravel
                                    # send_actual_attend_to_laravel(the_is_synced,
                                    #                               the_user_id,
                                    #                               the_effected_at,
                                    #                               the_type,
                                    #                               the_device,
                                    #                               the_template_position,
                                    #                               the_hash,
                                    #                               the_accuracy,
                                    #                               the_rfid_unique_id)

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
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(e).__name__, e.args)
            print(message)


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

                            the_first_name = db.table('users').where('id', user_related_with_this_rfid_card).pluck(
                                'first_name')
                            the_last_name = db.table('users').where('id', user_related_with_this_rfid_card).pluck(
                                'last_name')

                            our_result['first_name'] = the_first_name
                            our_result['last_name'] = the_last_name
                            our_result['last_action'] = 'None'

                            trigger_relay_on_enter()

                            db.table('user_logs').insert(is_synced=the_is_synced,
                                                         user_id=the_user_id,
                                                         effected_at=the_effected_at,
                                                         type=the_type,
                                                         device=the_device,
                                                         rfid_unique_id=the_rfid_unique_id)

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

                                        trigger_relay_on_enter()

                                        db.table('user_logs').insert(is_synced=the_is_synced,
                                                                     user_id=the_user_id,
                                                                     effected_at=the_effected_at,
                                                                     type=the_type,
                                                                     device=the_device,
                                                                     rfid_unique_id=the_rfid_unique_id)
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
                                                                     rfid_unique_id=the_rfid_unique_id)
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

                                    trigger_relay_on_enter()

                                    db.table('user_logs').insert(is_synced=the_is_synced,
                                                                 user_id=the_user_id,
                                                                 effected_at=the_effected_at,
                                                                 type=the_type,
                                                                 device=the_device,
                                                                 rfid_unique_id=the_rfid_unique_id)
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
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(e).__name__, e.args)
            print(message)

        finally:
            GPIO.cleanup()
            spi.closeSPI()

    else:
        sleep(1)


# def request_to_refresh_user_logs_table():
#     try:
#         url = 'http://yasna.local/attendance/api/v1/users/attends'  # @TODO: Must be dynamic later.
#
#         # Prepare the data
#         query_args = {
#             'is_synced': int(0),
#         }
#
#         header = {"Accept": "application/json",
#                   "Authorization": '760483978406f1195959ef81a90c91ef'
#                   }  # @TODO: Must be dynamic later.
#
#         data = urllib.urlencode(query_args)
#
#         # Send HTTP POST request
#         request = urllib2.Request(url, data, header)
#
#         # Sends the request and catches the response
#         response = urllib2.urlopen(request)
#
#         # Extracts the response
#         html = response.read()
#
#         print(html)
#
#     except Exception as e:
#         template = "An exception of type {0} occurred. Arguments:\n{1!r}"
#         message = template.format(type(e).__name__, e.args)
#         print(message)


schedule.every(handle_the_is_synced_field_period).seconds.do(handle_the_is_synced_field)
# schedule.every(300).seconds.do(request_to_refresh_user_logs_table)  # every 5 minutes

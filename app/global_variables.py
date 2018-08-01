# Timeouts
global settings_timeout
global enroll_finger_timeout
global working_hours
global enroll_rfid_timeout
global attendance_not_allowed_timeout

# Schedule periods
global handle_the_is_synced_field_period
global request_to_refresh_for_crud_on_laravel_period
global sync_users_period

# Maximum allowed fingers
global maximum_allowed_fingers_for_usual_users
global maximum_allowed_fingers_for_admin_users

# Device compatibility fields
global device_template_position_except_fingerprint
global device_hash_except_fingerprint
global device_accuracy_except_fingerprint
global rfid_unique_id_except_rfid

global DOMAIN


settings_timeout = 15  # 15 seconds
enroll_finger_timeout = 5  # 5 seconds
enroll_rfid_timeout = 5  # 5 seconds
working_hours = 39600  # 11 hours
attendance_not_allowed_timeout = 120  # 2 minutes

handle_the_is_synced_field_period = 60  # 1 minute
request_to_refresh_for_crud_on_laravel_period = 300  # 5 minutes
sync_users_period = 900  # 15 minutes

maximum_allowed_fingers_for_usual_users = 3
maximum_allowed_fingers_for_admin_users = 5

device_template_position_except_fingerprint = 5000
device_hash_except_fingerprint = 'No hash for this device.'
device_accuracy_except_fingerprint = -1
rfid_unique_id_except_rfid = 0

DOMAIN = 'yasna.local'

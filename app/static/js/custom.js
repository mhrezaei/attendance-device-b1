String.prototype.replaceAll = function (search, replacement) {
    var target = this;
    return target.replace(new RegExp(search, 'g'), replacement);
};

function forms_pd($string) {
    if (!$string) return;//safety!

    $string = $string.replaceAll(/1/g, "۱");
    $string = $string.replaceAll(/2/g, "۲");
    $string = $string.replaceAll(/3/g, "۳");
    $string = $string.replaceAll(/4/g, "۴");
    $string = $string.replaceAll(/5/g, "۵");
    $string = $string.replaceAll(/6/g, "۶");
    $string = $string.replaceAll(/7/g, "۷");
    $string = $string.replaceAll(/8/g, "۸");
    $string = $string.replaceAll(/9/g, "۹");
    $string = $string.replaceAll(/0/g, "۰");

    return $string;
}

function forms_digit_en(perDigit) {
    var newValue = "";
    for (var i = 0; i < perDigit.length; i++) {
        var ch = perDigit.charCodeAt(i);
        if (ch >= 1776 && ch <= 1785) // For Persian digits.
        {
            var newChar = ch - 1728;
            newValue = newValue + String.fromCharCode(newChar);
        }
        else if (ch >= 1632 && ch <= 1641) // For Arabic & Unix digits.
        {
            var newChar = ch - 1584;
            newValue = newValue + String.fromCharCode(newChar);
        }
        else
            newValue = newValue + String.fromCharCode(ch);
    }
    return newValue;
}

function pd(enDigit) {
    return forms_digit_fa(enDigit);
}

function ed(faDigit) {
    return forms_digit_en(faDigit);
}

function ad(digists) {
    if (getLocale() == 'fa') {
        return pd(digists);
    }
    return ed(digists);
}

function ad(string) {
    if ($.inArray(getLocale(), ['fa', 'ar']) > -1) {
        return pd(string);
    }
    return ed(string);
}

function forms_digit_fa(enDigit) {
    return forms_pd(enDigit);

    var newValue = "";
    for (var i = 0; i < enDigit.length; i++) {
        var ch = enDigit.charCodeAt(i);
        if (ch >= 48 && ch <= 57) {
            var newChar = ch + 1584;
            newValue = newValue + String.fromCharCode(newChar);
        }
        else {
            newValue = newValue + String.fromCharCode(ch);
        }
    }
    return newValue;
}

/**
 * Global Variables
 */
var App_router = "standby";
var App_modalState = "close";


/*
*-------------------------------------------------------
* Self Invoking Anonymous Function
*-------------------------------------------------------
*/
jQuery(function($){


    // StandBy theme
    checkTheme();
    setInterval(function () {
        checkTheme();
    },30000);


    //Modal close function
    $('#alertModal .close').on('click',closeModal);


    // Setting button clicked
    $('.js-accessSetting').on('click',function () {
        openModal('برای ورود به بخش تنظیمات انگشت‌ خود را اسکن کنید.', asset('images/fingerprint-with-keyhole.svg'));

        checkAdmin();
    });


    // Back To Home
    $('.back-to-home').on('click',closeSetting);



    // Socket
    //------------------------------------------------------------------

    let connected = false;

    const socket = io('http://' + document.domain + ':' + location.port);

    window.socket = socket;
    // On Connect
    socket.on('connect', function () {
        connected = true;
        console.log("connected");
    });


    // On Auth
    socket.on('auth', function (data) {
        console.log(data);
        socket.emit('setFingerPrintStatus', true);
    });


    // On fingerPrintStatus
    socket.on('fingerPrintStatus', function (data) {
        if (data.status <= 2) {
            console.log(data.status);
            noMatchFound();
        }
        if (data.status >= 3 && data.status <= 15) {
            console.log(data.status);
            console.log(data.last_action);

            let lastAction = "";
            console.log(data.last_action);
            if(data.last_action === "None" && data.last_action === "None"){
                lastAction = "ثبت نشده";
            }else {
                lastAction = toPersianDate(data.last_action) + " " + toPersianTime(data.last_action);
            }

            let msg = data.first_name + ' ' + data.last_name + 'خوش آمدید. آخرین خروج شما: ' + lastAction;
            openModal(msg, asset('images/welcome.svg'));
            setTimeout(closeModal, 3000);
        }

        if (data.status >= 16) {
            console.log(data.status);

            let lastAction = "";
            console.log(data.last_action);
            if(data.last_action === "None" && data.last_action === "None"){
                lastAction = "ثبت نشده";
            }else {
                lastAction = toPersianDate(data.last_action) + " ،" + toPersianTime(data.last_action);
            }

            if(data.last_action === "None" && data.last_action === "None"){
                lastAction = "ثبت نشده";
            }else {
                lastAction = toPersianDate(data.last_action) + " ،" + toPersianTime(data.last_action);
            }

            let msg = data.first_name + ' ' + data.last_name + 'خدا نگهدار. آخرین ورود شما: ' + lastAction;
            openModal(msg, asset('images/exit.svg'));
            setTimeout(closeModal, 3000);
        }

    });


    // On Disconnect
    socket.on('disconnect', function () {
        console.log('disconnected.');
        connected = false;
    });


    // Auto Update Socket
    setInterval(function () {
        if (connected){
            socket.emit('update');
        }
    }, 500);

//    socket.connect();

}); //End Of siaf!


/*
*-------------------------------------------------------
* Vue Related
*-------------------------------------------------------
*/

Vue.component('TimeAndDate', {
    template: `
        <div>
            <div class="time">
              {{ hour + ":" + min }}
            </div>
            <div class="date">
              {{ date }}
            </div>
        </div>
    `,
    data() {
        return {
            hour: null,
            min : null,
            date: null
        }
    },
    mounted() {
        var self = this;
        self.updateTime();
        setInterval(function () {
            self.updateTime();
        }, 30000)
    },
    methods : {
        getHour() {
            persianDate.toLocale('fa');
            this.hour = new persianDate().format('HH');
        },
        getMin() {
            persianDate.toLocale('fa');
            this.min = new persianDate().format('mm');
        },
        getDay() {
            persianDate.toLocale('fa');
            this.date = new persianDate().format('dddd D MMMM')
        },
        updateTime: function () {
            this.getHour();
            this.getMin();
            this.getDay();
        }
    }
});

Vue.component('app-clock', {
    template: `
      <div class="clock-widget" :class="theme">
           <div class="clock_bg">
               <img src="static/images/day.svg" class="dayIcon" alt="day icon">
               <img src="static/images/night.svg" class="nightIcon" alt="night icon">
           </div>
           <div class="clock_body">
               <TimeAndDate></TimeAndDate>
           </div>
       </div>
   `,
    data    : function () {
        return {
            theme: null,
        }
    },
    mounted : function () {
        var self = this;

        self.updateTime();
        setInterval(function () {
            self.updateTime();
        }, 30000)
    },
    methods : {
        checkDayLight: function () {
            persianDate.toLocale('en');
            let dayHour = new persianDate().format('HH');
            if (6 <= dayHour && dayHour < 19 ) {
                this.theme = "dayMode";
            } else {
                this.theme = "nightMode";
            }
        },
        updateTime   : function () {
            this.checkDayLight();
        }
    }

});

Vue.component('app-navbar', {
    template: `
        <nav id="navbar">
            <div class="navbar_container">
                <div class="logo">
                    <div class="logo_inner">
                        <div class="logo_image">
                            <img :src="logoSrc" alt="logo">
                        </div>
                        <div class="logo_title">
                            {{ title }}
                        </div>
                    </div>
                </div>
                <div class="time-and-date" v-show="showTime">
                    <TimeAndDate></TimeAndDate>
                </div>
            </div>
        </nav>
    `,
    props   : {
        isIndex: {
            type   : Boolean,
            default: false,
            require: true
        }
    },
    data    : function () {
        return {
            title   : "یسنا",
            logoSrc : '../static/images/logo-white.png',
            showTime: !this.isIndex
        }
    }
});

Vue.component('app-members-table',{
    template:
        `
        <div id="table" class="table-responsive">
            <table class="table table-bordered"> 
                <thead> 
                    <tr> 
                    <th style="width: 60px;">ردیف</th> 
                    <th>نام</th> 
                    <th>نام‌ خانوادگی</th> 
                    <th>کد‌ ملی</th> 
                    <th>عملیات</th> 
                    </tr> 
                </thead> 
                <app-row :rows="members"></app-row>
            </table> 
        </div>
        `,
    props:{
        members: Array,
    }
});

Vue.component('app-row',{
    template:
        `
        <tbody>
            <tr v-for="(row , index) in rows">
                <td>{{ convertDigit(index + 1) }}</td>
                <td>{{ row.first_name }}</td>
                <td>{{ row.last_name }}</td>
                <td>{{ convertDigit(row.code_melli) }}</td>
                <td class="table-action">
                    <button class="btn btn-lg btn-default actions" @click="showDetails(row)">جزئیات</button>
                </td>
            </tr>
        </tbody>
        `,
    props: {
        rows: Array,
    },
    methods: {
        showDetails: function (member) {
            getMemberReport(member)
        },
        convertDigit(digit){
            return pd(digit.toString())
        }
    }
});

Vue.component('app-details',{
    template:
            `
            <div class="member-tabs">
                <h3 class="tabs-title">{{ member.first_name + " " + member.last_name}}</h3>
                <ul class="nav nav-tabs">
                  <li class="active"><a data-toggle="tab" href="#member_attendance">لیست حضور و غیاب</a></li>
                  <li><a data-toggle="tab" href="#member_card">کارت</a></li>
                  <li><a data-toggle="tab" href="#member_fingerprint">اثر انگشت‌ها</a></li>
                  <li><a data-toggle="tab" href="#member_setting">تنظیمات</a></li>
                </ul>
                
                <div class="tab-content">
                  <div id="member_attendance" class="tab-pane fade in active">
                    <div class="table-responsive">
                        <table class="table table-bordered"> 
                            <thead> 
                                <tr> 
                                <th style="width: 60px;">ردیف</th> 
                                <th>تاریخ ورود</th> 
                                <th>ساعت ورود</th> 
                                <th>تاریخ خروج</th> 
                                <th>ساعت خروج</th> 
                                </tr> 
                            </thead> 
                            <tbody>
                                <tr v-for="(report , index) in reports">
                                    <td>{{ convertDigit(index + 1) }}</td>
                                    <td>{{ setDate(report.entered_at) }}</td>
                                    <td>{{ setTime(report.entered_at) }}</td>
                                    <td>{{ setDate(report.exited_at) }}</td>
                                    <td>{{ setTime(report.exited_at) }}</td>
                                </tr>
                            </tbody>
                        </table> 
                    </div>
                  </div>
                  <div id="member_card" class="tab-pane fade">
                    <div class="row" v-if="member.rfid_unique_id">
                        <div class="col-xs-4">
                            <div class="id-card-image">
                                <img src="static/images/id-card.svg" alt="id card">                            
                            </div>
                        </div>
                        <div class="col-xs-8">
                            <div class="card-info">
                            <span class="title">شماره کارت :</span>
                            <span class="card-id">{{ convertDigit(member.rfid_unique_id) }}</span>
                        </div>
                        <div class="controls">
                            <button class="btn btn-danger btn-lg" @click="removeCard">حذف کارت</button>
                        </div>
                        </div>
                    </div>
                    <div class="row" v-else>
                        <div class="col-xs-12">
                            <div class="alert alert-info">
                                <i class="fa fa-info-circle"></i>
                                برای این کاربر کارتی ثبت نشده.
                            </div>
                            <div class="controls">
                                <button class="btn btn-success btn-lg" @click="addNewCard">ثبت کارت</button>
                            </div>
                        </div>
                    </div>
                  </div>
                  <div id="member_fingerprint" class="tab-pane fade">
                    <div class="header">
                        <h3 class="title">تمام اثر انگشت‌ها</h3>
                    </div>
                    <div class="finger-print-list">
                        <table class="table table-bordered" v-if="member.related_fingers.length">
                            <thead>
                                <tr>
                                    <th style='width: 60px;'>ردیف</th>
                                    <th>شناسه</th>
                                    <th>نام</th>
                                    <th>عملیات</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="( fingerPrint , index ) in member.related_fingers">
                                    <td>{{ convertDigit(index + 1) }}</td>
                                    <td>{{ fingerPrint.id }}</td>
                                    <td>{{ fingerPrint.position }}</td>
                                    <td style="text-align: center;">
                                        <button class="btn btn-lg btn-danger" @click="removeThisFingerPrint(fingerPrint.id)">حذف</button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                        <div class="alert alert-info" v-else>
                            <i class="fa fa-info-circle"></i>
                            برای این کاربر اثر انگشتی ثبت نشده‌است.
                        </div>
                    </div>
                    <div class="controls">
                            <button class="btn btn-lg btn-success" @click="addNewFingerPrint">اثر انگشت جدید</button>  
                            <!--<button class="btn btn-lg btn-danger" -->
                            <!--v-if="member.fingerPrints.length"-->
                            <!--@click="removeAll">-->
                            <!--حذف همه-->
                            <!--</button>-->
                        </div>
                  </div>
                  <div id="member_setting" class="tab-pane fade">
                    <button class="btn btn-lg btn-danger" @click="removeUser">
                        <i class="fa fa-ban"></i>
                        حذف کاربر
                    </button>
                  </div>
                </div>
            </div>
            `,
    props: ['member','reports'],
    methods:{
        setTime: function (date) {
            return toPersianTime(date);
        },
        setDate: function (date) {
            return toPersianDate(date);
        },
        convertDigit(digit){
            return pd(digit.toString())
        },
        removeUser: function () {
            removeMember(this.member.id);
        },
        removeThisFingerPrint: function (id) {
            removeFingerPrint(id, this.reports);
        },
        removeAll: function () {
            removeAllFingerPrints(this.member)
        },
        addNewFingerPrint: function () {
            var member = this.member;
            var reports = this.reports;
            addNewFingerPrint(member,reports);
        },
        removeCard: function () {
            removeMemberCard(this.member, this.reports);
        },
        addNewCard: function () {
            addNewCard(this.member, this.reports);
        }

    }
});

var Daytime = function () {
  persianDate.toLocale('en');
  this.hour = new persianDate().format('HH');

  this.isDay = function () {
      return (6 <= this.hour && this.hour < 19);
  };

  this.isNight = function () {
      return (this.hour < 6 || this.hour >= 19);
  };
};

var vm = new Vue({
    el: "#app"
});

/*
*-------------------------------------------------------
* Vanilla JavaScript
*-------------------------------------------------------
*/


/**
 * Opens Modal
 * @param message
 * @param iconSrc
 */
function openModal(message, iconSrc) {
    var modal = $('#alertModal');
    var src   = (iconSrc && iconSrc.length) ? iconSrc : asset("images/warning.svg");
    modal.find('img').attr('src', src);
    modal.find('.message').text(message);
    modal.addClass('show');

    App_modalState = "open";
}


/**
 * Closes Modal
 */
function closeModal() {
    if(App_modalState === "close"){
        return
    }

    var modal = $('#alertModal');
    var src   = asset("images/warning.svg");
    modal.find('.icon img').attr('src', src);
    modal.find('.message').text("");
    modal.removeClass('show');

    App_modalState = "close";
}


/**
 * Changes Theme According To Time.
 */
function checkTheme() {
    var daytime = new Daytime();

    if (daytime.isDay()){
        $('#standby').removeClass('night').addClass('day');
    }

    if (daytime.isNight()){
        $('#standby').removeClass('day').addClass('night');
    }
}


/**
 * Opens Setting Page
 */
function openSetting() {
    if(App_router === "setting"){
        return
    }

    $('body').addClass('showSetting');

    App_router = "setting";
}


/**
 * Closes Setting Page
 */
function closeSetting() {
    if(App_router !== "setting"){
        return
    }

    $('body').removeClass('showSetting');
    clearList();
    App_router = "standby";
    socket.emit('setFingerPrintStatus', true);
}


/**
 * Clear List Element
 */
function clearList() {
    $('#list').html("");
}


/**
 * Converts TimeStamp To Persian Date
 * @param timeStamp
 * @returns {string}
 */
function toPersianDate(timestamp){
    if(timestamp === "None"){
        return "ثبت نشده";
    }
    var unix = new persianDate(new Date(timestamp)).valueOf();
    return new persianDate(unix).toLocale('fa').toCalendar('persian').format('HH:mm');
}


/**
 * Converts Timestamp To Persian Time
 * @param timestamp
 * @returns {string}
 */
function toPersianTime(timestamp) {
    if(timestamp === "None"){
        return "ثبت نشده";
    }
    var unix = new persianDate(new Date(timestamp)).valueOf();
    return new persianDate(unix).toLocale('fa').toCalendar('persian').format('DD MMMM YYYY');
}


/**
 * Loading Modal
 */
function waitForIt() {
    openModal('لطفا منتظر باشید...', asset('images/sand-clock.svg'))
}


/**
 * Actions If Connection Has Error
 */
function connectionError() {
    openModal('اختلال در شبکه',asset("images/fingerprint-information-symbol.svg"));

}


/**
 * Actions If Is Admin
 */
function isAdmin(members) {
    closeModal();
    openSetting();
    getMembersList(members);
}


/**
 * Actions If Is Not Admin
 */
function isNotAdmin() {
    openModal("شما اجازه دسترسی به این بخش را ندارید.", asset('images/fingerprint-outline-with-close-button.svg'));
    setTimeout(function () {
        closeModal()
    },3000);
}


/**
 * Actions If No Match Found
 */
function noMatchFound() {
    openModal('اطلاعات شما در سیستم یافت نشد.', asset('images/fingerprint-with-question-mark.svg'));
    setTimeout(function () {
        closeModal()
    },3000);
}


/**
 * Actions If Time Out
 */
function scanTimeout() {
    closeModal();
}


/**
 * Ajax - Check Accessibility
 */
function checkAdmin() {
    socket.emit('setFingerPrintStatus', false);
    $.ajax({
        url: url("settings_process"),
        dataType: "json",
        success: function(response) {
            // If Not admin
            if(response.status === 203){
                socket.emit('setFingerPrintStatus', true);
                isNotAdmin();
                return;
            }

            // If No Match Found
            if(response.status === 204){
                socket.emit('setFingerPrintStatus', true);
                noMatchFound();
                return;
            }

            // If Timeout
            if(response.status === 205){
                socket.emit('setFingerPrintStatus', true);
                scanTimeout();
                return;
            }

            // If Admin
            if (response.status === 202){
                isAdmin(response.members);
                return;
            }
        },
        error: connectionError
    });

}


/**
 * Gets Members List
 */
function getMembersList(members) {
    if(App_router !== "setting"){
        return
    }

    renderMembers(members);
}


/**
 * Renders Members List
 * @param members
 */
function renderMembers(members) {
    clearList();
    $('<app-members-table :members="members"></app-members-table>')
        .appendTo('#list');

    new Vue({
        el: "#list",
        data: {
            members: members,
        }
    });
}


/**
 * Ajax - Gets Member Detail
 * @param member
 */
function getMemberReport(member) {
    var id = member.id;

    waitForIt();

    $.ajax({
        url: url('user_logs_process'),
        dataType: "json",
        type: "POST",
        data: {
            user_id: id
        },
        success: function (response) {
            closeModal();

            // If User has no log
            if(response.status === 302){
                var reports = [];
                renderMemberDetails(member,reports);
                return;
            }

            // If user has logs
            if(response.status === 301){
                renderMemberDetails(member, response.reports);
                return;
            }
        },
        error: connectionError
    })
}


/**
 * Renders Member Details
 * @param member
 * @param reports
 */
function renderMemberDetails(member, reports) {
    clearList();
    $('<app-details :member="member" :reports="reports"></app-details>').appendTo('#list');

    new Vue({
        el: "#list",
        data: {
            member: member,
            reports: reports
        }
    })
}


/**
 * Ajax - Removes Member From List
 * @param id
 */
function removeMember(id){
    $.ajax({
        url: "../static/js/data/members-list.json",  //@TODO: This should get new members list.
        dataType: "json",
        type: "POST",
        data:{
            id: id
        },
        success: function (response) {
            renderMembers(response.member[0]);
        },
        error: function () {
            showError('خطا در برقراری ارتباط','#list');
        }
    })
}


/**
 * Ajax - Removes A Specific FingerPrint
 * @param fingerId
 * @param member
 */
function removeFingerPrint(fingerId, reports) {
    waitForIt();

    $.ajax({
        url: '../static/js/data/member.json', //@TODO: This should get new member detail.
        dataType: "json",
        type: "POST",
        data:{
            fingerId: fingerId
        },
        success: function (response) {
            closeModal();
            renderMemberDetails(response.member[0], reports);
        },
        error: connectionError
    })
}


/**
 * Ajax - Removes All FingerPrints Of A Specific Member
 * @param member
 */
function removeAllFingerPrints(member) {
    var id = member.id;
    $.ajax({
        url: '../static/js/data/member'+ id +'.json', //@TODO: This should get new member detail.
        dataType: "json",
        type: "POST",
        data:{
            id: id
        },
        success: function (response) {
            renderMemberDetails(member, response.reports);
        },
        error: function () {
            showError('خطا در برقراری ارتباط','#list');
        }
    })
}


/**
 * Ajax - Adds New FingerPrint For A Member
 * @param member
 */
function addNewFingerPrint(member,reports) {
    var id = member.id;

    openModal("انگشت خود را روی دستگاه قرار دهید.",asset("images/fingerprint-scanning-in-half-view.svg"));

    $.ajax({
        url: url('enroll_handle_finger_step_1'),
        dataType: "json",
        type: "POST",
        data:{
            user_id: id
        },
        success: function (response) {
            if(response.status === 401){
                openModal('این انگشت قبلا ثبت شده‌است.',asset('images/fingerprint-outline-with-close-button.svg'));
                return
            }

            if(response.status === 403){
                scanTimeout();
                return
            }

            if(response.status === 402){
                openModal('لطفا انگشت خود را بردارید.', asset("images/sand-clock.svg"));
                setTimeout(function () {
                    openModal('انگشت خود را مجددا روی دستگاه قرار دهید.', asset("images/fingerprint-scanning-in-half-view.svg"));
                    addNewFingerStep2(id, reports)
                },3000);
                return;
            }

        },
        error: connectionError
    })
}


/**
 * Ajax - Adds New FingerPrint For A Member (Rendering)
 * @param id
 * @param reports
 */
function addNewFingerStep2(id, reports) {

    $.ajax({
        url: url('enroll_handle_finger_step_2'),
        dataType: "json",
        success: function (response) {
            // No Match
            if(response.status === 411){
                openModal('عدم مطابقت با اثر انگشت قبلی',asset('images/fingerprint-outline-with-close-button.svg'));
                return
            }

            // Timeout
            if(response.status === 414){
                scanTimeout();
                return
            }

            // Match and saved
            if(response.status === 413){
                openModal('اثر انگشت با موفقیت ثبت شد.',asset('images/fingerprint-outline-with-check-mark.svg'));
                setTimeout(function () {
                    closeModal();
                    renderMemberDetails(response.member[0], reports);
                },3000);
            }

        },
        error: connectionError
    })
}


/**
 * Ajax - Remove Member Card
 * @param member
 */
function removeMemberCard(member, reports) {
    var id = member.id;

    waitForIt();

    $.ajax({
        url: '../static/js/data/member.json', //@TODO: This should get new member detail.
        dataType: "json",
        type: "POST",
        data:{
            user_id: id
        },
        success: function (response) {
            closeModal();
            renderMemberDetails(response.member[0], reports);
        },
        error: connectionError
    })
}



function addNewCard(member,reports) {
    var id = member.id;

    waitForIt();

    $.ajax({
        url: '../static/js/data/member.json', //@TODO: This should get new member detail.
        dataType: "json",
        type: "POST",
        data:{
            user_id: id
        },
        success: function (response) {
            closeModal();
            renderMemberDetails(response.member[0], reports);
        },
        error: connectionError
    })
}

/**
 * Shows Error Message
 * @param message
 * @param parent
 */
function showError(message,parent) {

    $("<div class=\'message\'></div>")
        .appendTo(parent)
        .text(message)
}



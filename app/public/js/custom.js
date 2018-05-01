/**
 * Global Variables
 */
var App_router = "standby";
var App_modalState = "close";

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
               <img src="../public/images/day.svg" class="dayIcon" alt="day icon">
               <img src="../public/images/night.svg" class="nightIcon" alt="night icon">
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
            if (6 < dayHour < 19) {
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
            logoSrc : '../public/images/logo-white.png',
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
                <td>{{ index + 1 }}</td>
                <td>{{ row.name }}</td>
                <td>{{ row.lastName }}</td>
                <td>{{ row.codeMelli }}</td>
                <td class="table-action"><button class="btn btn-default actions" @click="showDetails(row)">عملیات</button></td>
            </tr>
        </tbody>
        `,
    props: {
        rows: Array,
    },
    methods: {
        showDetails: function (member) {
            showMember(member)
        }
    }
});

Vue.component('app-details',{
    template:
            `
            <div class="member-tabs">
                <h3 class="tabs-title">{{ member.name + " " + member.lastName}}</h3>
                <ul class="nav nav-tabs">
                  <li class="active"><a data-toggle="tab" href="#member_attendance">لیست حضور و غیاب</a></li>
                  <li><a data-toggle="tab" href="#memeber_card">کارت</a></li>
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
                                    <td>{{ index + 1 }}</td>
                                    <td>{{ report.enter_date }}</td>
                                    <td>{{ report.enter_time }}</td>
                                    <td>{{ report.exit_date }}</td>
                                    <td>{{ report.exit_time }}</td>
                                </tr>
                            </tbody>
                        </table> 
                    </div>
                  </div>
                  <div id="memeber_card" class="tab-pane fade">
                    <h3>نمایش کارت</h3>
                    <p>Some content in menu 1.</p>
                  </div>
                  <div id="member_fingerprint" class="tab-pane fade">
                    <h3>اثر انگشت‌ها</h3>
                    <p>Some content in menu 2.</p>
                  </div>
                  <div id="member_setting" class="tab-pane fade">
                    <h3>تنظیمات</h3>
                    <p>Some content in menu 2.</p>
                  </div>
                </div>
            </div>
            `,
    props: ['member','reports'],
});

var Daytime = function () {
  persianDate.toLocale('en');
  this.hour = new persianDate().format('HH');

  this.isday = function () {
      return 6 < this.hour && this.hour < 19;
  };

  this.inNight = function () {
      return this.hour < 6 && this.hour > 19;
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
    var src   = (iconSrc && iconSrc.length) ? iconSrc : "../public/images/warning.svg";
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
    var src   = "../public/images/warning.svg";
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

    if (daytime.isday()){
        $('#standby').removeClass('night').addClass('day');
    }

    if (daytime.inNight()){
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

    App_router = "standby";
}


/**
 * Actions If Is Admin
 */
function isAdmin() {
    setTimeout(function () {
        closeModal();
        openSetting();
        getMembersList();
    },3000);
}


/**
 * Actions If Is Not Admin
 */
function isNotAdmin() {
    setTimeout(function () {
        openModal("شما اجازه ورود به این بخش را ندارید.","../public/images/fingerprint-outline-with-close-button.svg");
    },3000);
}


function clearList() {
    $('#list').html("");
}


/**
 * Ajax - Gets Members List
 */
function getMembersList() {
    if(App_router !== "setting"){
        return
    }

    $.ajax({
        url: "../public/js/data/members-list.json",
        dataType: "json",
        success: function (response) {
            renderMembers(response.members);
        },
        error: function () {
            showError('خطا در برقراری ارتباط','#list');
        }
    })
}

function getMemberReport(id) {
    $.ajax({
        url: "../public/js/data/member1.json",
        dataType: "json",
        success: function (response) {
            return response.reports;
        },
        error: function () {
            showError('خطا در برقراری ارتباط','#member_attendance');
        }
    })
}

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


function showError(message,parent) {

    $("<div class=\'message\'></div>")
        .appendTo(parent)
        .text(message)
}

function showMember(member) {
    clearList();
    $('<app-details :member="member" :reports="reports"></app-details>').appendTo('#list');

    new Vue({
        el: "#list",
        data:{
            member: member,
            reports: null
        },
        created: function () {
            var id = this.member.id;
            var reports = this.reports;

            $.ajax({
                url: "../public/js/data/member1.json",
                dataType: "json",
                success: function (response) {
                    reports = response.reports;
                },
                error: function () {
                    showError('خطا در برقراری ارتباط','#member_attendance');
                }
            })
        }
    })
}

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
        openModal('برای ورود به بخش تنظیمات مجددا انگشت‌ خود را اسکن کنید.', '../public/images/fingerprint-with-keyhole.svg');
        $.ajax({
            url: "../public/js/data/isAdmin.json",
            dataType: "json",
            success: function(response) {
                if(response.isAdmin){
                    isAdmin();
                }else {
                    isNotAdmin();
                }
            },
            error: function () {
                openModal('مجددا تلاش کنید.','../public/images/fingerprint-information-symbol.svg');
            }
        });
    });


    // Back To Home
    $('.back-to-home').on('click',closeSetting);



}); //End Of siaf!

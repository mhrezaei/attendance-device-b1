
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

new Vue({
    el: "#app"
});

function openModal(message, iconSrc) {
    var modal = $('#alertModal');
    var src   = (iconSrc && iconSrc.length) ? iconSrc : "../public/images/warning.svg";
    modal.find('img').attr('src', src);
    modal.find('.message').text(message);
    modal.addClass('show');
}

function closeModal() {
    var modal = $('#alertModal');
    var src   = "../public/images/warning.svg";
    modal.find('.icon img').attr('src', src);
    modal.find('.message').text("");
    modal.removeClass('show');
}

function checkTheme() {
    var daytime = new Daytime();

    if (daytime.isday()){
        $('#standby').removeClass('night').addClass('day');
    }

    if (daytime.inNight()){
        $('#standby').removeClass('day').addClass('night');
    }
}

$(document).ready(function () {
    //Modal close function
    $('#alertModal').on('click',closeModal);

    // StandBy theme
    checkTheme();
    setInterval(function () {
        checkTheme();
    },30000);


});
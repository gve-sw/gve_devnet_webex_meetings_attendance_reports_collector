function convertToCSV(objArray) {
    var array = typeof objArray != 'object' ? JSON.parse(objArray) : objArray;
    var str = '';
    for (var i = 0; i < array.length; i++) {
        var line = '';
        for (var index in array[i]) {
            if (line != '') line += ','
            line += array[i][index];
        }
        str += line + '\r\n';
    }
    return str;
}

function exportCSVFile(headers, items, fileTitle) {
    if (headers) {
        items.unshift(headers);
    }
    // Convert Object to JSON
    var jsonObject = JSON.stringify(items);
    var csv = this.convertToCSV(jsonObject);
    var exportedFilenmae = fileTitle + '.csv' || 'export.csv';
    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });

    if (navigator.msSaveBlob) { // IE 10+
        navigator.msSaveBlob(blob, exportedFilenmae);
    } else {
        var link = document.createElement("a");
        if (link.download !== undefined) { // feature detection
            // Browsers that support HTML5 download attribute
            var url = URL.createObjectURL(blob);
            link.setAttribute("href", url);
            link.setAttribute("download", exportedFilenmae);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
}

$(document).ready(function($) {
    $(".loader").css("display", "none");
    $(".page-overlay").css("display", "none");

    // Pre-fill meetings list with today
    setTimeout(
        function() {
            let date = $('#dateSelect').val()
            let start = date.substr(0, date.indexOf('-')-1)+'T00:00:00'
            start = start.replaceAll('/', '-')
            let end = date.substr(date.indexOf('-')+2, date.length-1)+'T00:00:00'
            end = end.replaceAll('/', '-')
            $(".loader").css("display", "block");
            $(".page-overlay").css("display", "block");
            $.ajax({
                url: '/retrieve-meetings',
                type: "POST",
                data: JSON.stringify({ 'from': start, 'to': end }),
                contentType:"application/json; charset=utf-8",
                dataType:"json",
                success: function(data){
                    $("#meetings-list").empty();
                    if (data.items.length < 1) {
                        $("#meetings-list").append('<li class="list-group-item">No Meetings for Date Range</li>')
                    } else {
                        for (let i=0;i<data.items.length;i++) {
                            let meeting = data.items[i];
                            $("#meetings-list").append(
                                // '<li class="list-group-item">Meeting ' + meeting.id + ': ' + meeting.title + '</li>'
                                `<li class="list-group-item"><a href="#" class="list-group-item-action flex-column align-items-start">
                                    <div class="d-flex w-100 justify-content-between">
                                    <h5 class="mb-1">${meeting.title}</h5>
                                    <small>${meeting.start}</small>
                                    </div>
                                    <p class="mb-1">Meeting Number: ${meeting.meetingNumber}, ${meeting.meetingType}, Ended ${meeting.end} ${meeting.timezone}</p>
                                    <small>Hosted by ${meeting.hostDisplayName}</small>
                                </a></li>`
                            )
                            $('#generate-report').prop('disabled', false);
                        }
                    }
                    $(".loader").css("display", "none");
                    $(".page-overlay").css("display", "none");
                }
            })
        }, 1);

    let meetingsNum = $("#meetings-list a").length
    if ($("#meetings-list a").length < 1)
        $("#meetings-list").append('<li class="list-group-item">No Meetings for Date Range</li>')

    $(document).on('click', '#generate-report', function(event) {
        event.preventDefault();
        // Get date range
        let date = $('#dateSelect').val()
        let start = date.substr(0, date.indexOf('-')-1)+'T00:00:00'
        start = start.replaceAll('/', '-')
        let end = date.substr(date.indexOf('-')+2, date.length-1)+'T00:00:00'
        end = end.replaceAll('/', '-')

        $(".loader").css("display", "block");
        $(".page-overlay").css("display", "block");

        $.ajax({
                url: '/generate-report',
                type: "POST",
                data: JSON.stringify({ 'from': start, 'to': end }),
                contentType:"application/json",
                dataType:"json",
                success: function(r){
                    $(".loader").css("display", "none");
                    $(".page-overlay").css("display", "none");
                    // convert to csv
                    // console.log(r);
                    var file = r.items;
                    var headers = {
                        id: 'id',
                        orgId: "orgId",
                        host: "host",
                        coHost: "coHost",
                        spaceModerator: "spaceModerator",
                        email: "email",
                        displayName: "displayName",
                        invitee: "invitee",
                        muted: "muted",
                        state: "state",
                        joinedTime: "joinedTime",
                        leftTime: "leftTime",
                        siteUrl: "siteUrl",
                        meetingId: "meetingId",
                        hostEmail: "hostEmail",
                        // devices: "devices"
                    };
                    // "id", "orgId", "host", "coHost", "spaceModerator", "email", "displayName", "invitee", "muted", "state", "joinedTime", "leftTime", "siteUrl", "meetingId", "hostEmail", "devices"
                    let itemsNotFormatted = file;
                    var itemsFormatted = [];

                    // format data
                    itemsNotFormatted.forEach((item) => {
                        itemsFormatted.push({
                            id: item.id,
                            orgId: item.orgId,
                            host: item.host,
                            coHost: item.coHost,
                            spaceModerator: item.spaceModerator,
                            email: item.email,
                            displayName: item.displayName,
                            invitee: item.invitee,
                            muted: item.muted,
                            state: item.state,
                            joinedTime: item.joinedTime,
                            leftTime: item.leftTime,
                            siteUrl: item.siteUrl,
                            meetingId: item.meetingId,
                            hostEmail: item.hostEmail,
                            // devices: item.devices
                        });
                    });
                    // generate filename based on date-time meeting-participants
                    var fileTitle = "meeting-participants-{{ sysTime }}";
                    // call the exportCSVFile() function to process the JSON and trigger the download
                    exportCSVFile(headers, itemsFormatted, fileTitle);
                }
        })
  });

  $('input[name="daterange"]').daterangepicker({
    maxDate: new Date(),
    opens: 'left',
    locale: {format: 'YYYY/MM/DD'}
    }, function(start, end, label) {
        $(".loader").css("display", "block");
        $(".page-overlay").css("display", "block");
        // Generate list for meetings
        $.ajax({
            url: '/retrieve-meetings',
            type: "POST",
            data: JSON.stringify({ 'from': start.format('YYYY-MM-DD')+'T00:00:00', 'to': end.format('YYYY-MM-DD')+'T00:00:00' }),
            contentType:"application/json; charset=utf-8",
            dataType:"json",
            success: function(data){
                $(".loader").css("display", "none");
                $(".page-overlay").css("display", "none");
                $("#meetings-list").empty();
                if (data.items.length < 1) {
                    $("#meetings-list").append('<li class="list-group-item">No Meetings for Date Range</li>')
                } else {
                    for (let i=0;i<data.items.length;i++) {
                        let meeting = data.items[i];
                        // $("#meetings-list").append('<li class="list-group-item">Meeting ' + meeting.id + ': ' + meeting.title + '</li>')
                        $("#meetings-list").append(
                                `<li class="list-group-item"><a href="javascript:;" class="list-group-item-action flex-column align-items-start">
                                    <div class="d-flex w-100 justify-content-between">
                                    <h5 class="mb-1">${meeting.title}</h5>
                                    <small>${meeting.start}</small>
                                    </div>
                                    <p class="mb-1">Meeting Number: ${meeting.meetingNumber}, ${meeting.meetingType}, Ended ${meeting.end} ${meeting.timezone}</p>
                                    <small>Hosted by ${meeting.hostDisplayName}</small>
                                </a></li>`
                        )
                        $('#generate-report').prop('disabled', false);
                    }
                }
            }
        })
    });
});
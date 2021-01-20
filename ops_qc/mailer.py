# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import datetime
import logging

import pytz

from ops_core.mailer import MandrillMailer, parse_address
from .utils import *


ALERT_SUBJECT = "Mangopare Temperature and Depth Data for {} from {} to {}"

ALERT_CANCEL_SUBECT = "[{level}] StormWatch for {site} - Risk of Extreme Weather Cancelled"

BODY_STYLE = """
<style>
.logo {
    position: absolute;
}
img {
    display: block;
    margin: auto;
}
table td th {
    border: 1px solid black;
    margin: auto;
}
td {
    padding: 2px 20px;
}
</style>
"""


ALERT_BODY_HTML = """
<html>
<head>
{style}
</head>
<body>
<img style="float: right;" src="https://ui.metoceanview.com/dist/images/msl.png">
<p style="font-size:x-large;"><strong>LEVEL:</strong> <span style="color: {color}; font-weight: bold">{level}</p>
<p style="font-size:x-large;"><strong>ETA:</strong> {eta}</p>
<table>
    <thead><tr><th>Forecast site info</th></tr><thead>
    <tbody>
    <tr><td style="font-weight: bold;">Site name: </td><td>{site}</td></tr>
    <tr><td style="font-weight: bold;">Coordinates: </td><td> {lat}, {lon}</td></tr>
    <tr><td style="font-weight: bold;">Time Zone: </td><td> {timezone}</td></tr>
    </tbody>
</table>
<p>The latest forecast guidance suggests the worst case scenario will exceed the safety threshold at {alert_at}.</p>
{alert_table}
<p>The graph below displays colored-coded alert time-frames (red, orange, yellow) when the forecast exceed the given thresholds.<p>
{plots}
<p>Latest forecast cycle at {cycle} UTC.</p>
<p>Estimation produced at {issued_at}.</p>
<img style="float: right;" src="https://ui.metoceanview.com/dist/images/msl.png">
</body>
</html>
"""

ALERT_CANCEL_BODY_HTML = """
<html>
<head>
{style}
</head>
<body>
<img style="float: right;" src="https://ui.metoceanview.com/dist/images/msl.png">
<p style="font-size:x-large;"><strong>LEVEL:</strong> <span style="color: {color}; font-weight: bold">{level}</p>
<table>
    <thead><tr><th>Forecast site info</th></tr><thead>
    <tbody>
    <tr><td style="font-weight: bold;">Site name: </td><td>{site}</td></tr>
    <tr><td style="font-weight: bold;">Coordinates: </td><td> {lat}, {lon}</td></tr>
    <tr><td style="font-weight: bold;">Time Zone: </td><td> {timezone}</td></tr>
    </tbody>
</table>
<p>The latest forecast guidance suggests the worst case scenario will not exceed safety thresholds.</p>
{plots}
<p>Latest forecast cycle at {cycle} UTC.</p>
<p>Estimation produced at {issued_at}.</p>
<img style="float: right;" src="https://ui.metoceanview.com/dist/images/msl.png">
</body>
</html>
"""

ALERT_BODY_TEXT = """
    LEVEL: {level}
    ETA: {eta}
    The latest forecast guidance suggests the worst case scenario will exceed the safety threshold at {alert_at}.

    Latest forecast cycle {cycle} UTC.
    Estimation produced at {issued_at}.
"""

ALERT_CANCEL_BODY_TEXT = """
    LEVEL: {level}
    The latest forecast guidance suggests the worst case scenario will not exceed safety thresholds.

    Latest forecast cycle {cycle} UTC.
    Estimation produced at {issued_at}.
"""



class StormWatchMailer(object):
    """docstring for StormWatchMailer"""
    def __init__(self, site, evaluators, plots, cycle_dt,
                 recipients,
                 from_email,
                 bcc=[],
                 reply_to=None,
                 logger=logging):
        super(StormWatchMailer, self).__init__()
        self.site = site
        self.evaluators = evaluators
        self.plots = plots
        self.cycle_dt = cycle_dt
        self.from_email = from_email
        self.recipients = recipients
        self.bcc = bcc
        self.reply_to = reply_to
        self.logger = logger
        self.mailer =  MandrillMailer()

    def _get_plots(self):
        plots = ""
        for plot in self.plots:
            plots += ('<p><img src="cid:%s"></p>'%os.path.basename(plot))+os.linesep
        return plots

    def _get_alert_level(self):
        alert_at = datetime.datetime(2999,1,1).replace(tzinfo=pytz.UTC)
        level = 'OK'
        color = get_alert_color(level)
        for evaluator in self.evaluators:
            if evaluator.alert_at and evaluator.alert_at < alert_at:
                alert_at = evaluator.alert_at
                level = evaluator.alert_level
                color = evaluator.alert_color

        return alert_at, level, color

    def _get_context(self):
        timezone = pytz.timezone(self.site.timezone)
        now = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        now = now.astimezone(timezone)
        utcoff = now.utcoffset()
        alert_at, level, color = self._get_alert_level()
        if now > alert_at:
            eta_str = 'ongoing'
        else:
            eta_str = str(alert_at-now).split(".")[0]
        context = {
             'level': level,
             'id'   : self.site.id,
             'alert_table': self.get_alert_table(int(utcoff.total_seconds()/3600)),
             'style' : BODY_STYLE,
             'eta'  : eta_str,
             'alert_at': alert_at.strftime('%d/%m/%y %H:%M'),
             'color' : color,
             'plots' : self._get_plots(),
             'issued_at' : now.strftime('%Y-%m-%d %H:%M:%S%z'),
             'cycle' : self.cycle_dt,
        }
        context.update(self.get_forecast_site_info())
        return context

    def has_been_alerted(self):
        now = datetime.datetime.utcnow()
        params = {
            'query': 'subject:%s' % self.site.name,
            'senders':[parse_address(self.from_email)['email']],
            'date_from': (now-datetime.timedelta(hours=24)).date().isoformat(),
            'limit': 1
        }

        last_email = self.mailer.mandrill.messages.search(**params)

        if last_email and 'Detected' in last_email[0]['subject']:
            return True
        else:
            return False

    def get_alert_table(self, utcoffset):
        table = """<table>"""
        table += "<thead><tr><th>Time (UTC+{utcoffset}h)</th><th>Reason</th><th>Alert Level</th></tr></thead>\n<tbody>"
        row = '<tr><td>%d/%m/%y %H:%M</td><td>%%s</td><td style="color: %%s;">%%s</td></tr>\n'
        content = {}
        for evaluator in self.evaluators:
            for dt in evaluator.alerts.index[evaluator.alerts.alerting]:
                __, __, level, color = evaluator.get_alert_level(dt)
                if dt not in content:
                    content[dt] = []
                content[dt].append(evaluator.alerts.reason[dt])
        for dt in sorted(content):
            reasons = content[dt]
            __, __, level, color = evaluator.get_alert_level(dt)
            dt_row = dt.strftime(row) % (', '.join(reasons), color, level)
            table += dt_row
        table += "</tbody></table>"
        return table.format(utcoffset=utcoffset)

    def get_forecast_site_info(self):
        lon_card = 'E' if self.site.x >=0 else 'W'
        lat_card = 'N' if self.site.y >=0 else 'S'
        info = {
            'site' : self.site.name,
            'lon'  : '%.3f°%s' % (abs(self.site.x), lon_card),
            'lat'  : '%.3f°%s' % (abs(self.site.y), lat_card),
            'timezone': self.site.timezone,
        }
        return info

    def send_alert_email(self):
        self.logger.info('Sending ALERT email to %d recipients...' %\
                                                 len(self.recipients))
        context = self._get_context()
        subject = ALERT_SUBJECT.format(**context)
        html = ALERT_BODY_HTML.format(**context)
        text = ALERT_BODY_TEXT.format(**context)
        self.mailer.send_email(to=self.recipients, bcc=self.bcc,
                          subject=subject,
                          html=html,
                          text=text,
                          from_=self.from_email,
                          reply_to=self.reply_to,
                          images=self.plots,
                          important=True)


    def send_cancelation_email(self):
        self.logger.info('Sending cancellation email to %d recipients...' %\
                                                     len(self.recipients))
        context = self._get_context()
        subject = ALERT_CANCEL_SUBECT.format(**context)
        html = ALERT_CANCEL_BODY_HTML.format(**context)
        text = ALERT_CANCEL_BODY_TEXT.format(**context)
        self.mailer.send_email(to=self.recipients, bcc=self.bcc,
                          subject=subject,
                          html=html,
                          text=text,
                          from_=self.from_email,
                          reply_to=self.reply_to,
                          images=self.plots,
                          important=True)

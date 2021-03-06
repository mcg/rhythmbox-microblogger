#! /usr/bin/python2
# -*- coding: utf8 -*-
#
# Rhythmbox-Microblogger - <http://github.com/aliva/Rhythmbox-Microblogger>
# Copyright (C) 2010 Ali Vakilzade <ali.vakilzade in Gmail>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import base64
import hashlib
import hmac
import libxml2
import pynotify
import random
import time
import urlparse
import urllib
import urllib2
import webbrowser
import oauth2 as oauth

IDENTICA={
    'key'   :'NzljNWU2MDFjNmQzMTU0ZDRhMTkwMTRmZmI1MWU2Zjk=',
    'secret':'YzgyYmJiZDg3NWVlYmM2ZWZkODA3OTEwYjg3M2VhMDk=',
    'request_token':'https://identi.ca/api/oauth/request_token',
    'access_token' :'https://identi.ca/api/oauth/access_token',
    'authorization':'https://identi.ca/api/oauth/authorize',
    'post':'https://identi.ca/api/statuses/update.json',
    'call_back':'oob',
    'maxlen':140,
}

TWITTER={
    'key'   :'NlFmM0JtVmpETk1UOUlYek9oa1E0Zw==',
    'secret':'QVd6SnBldWNvM0dPU0pXRlpGcGJpeXlJOGNlSnRWb1k4TmRZdHQzVVpn',
    'request_token':'https://twitter.com/oauth/request_token',
    'access_token' :'https://twitter.com/oauth/access_token',
    'authorization':'https://twitter.com/oauth/authorize',
    'post': 'https://twitter.com/statuses/update.json',
    'call_back':None,
    'maxlen':140,
}

GETGLUE={
    'key'   :'YzAzMGU0NGUxZmJmNzllZWU4Zjg2YjA0ZDAzNGYxZWI=',
    'secret':'NWEyZjc5M2FhMGVlNTBhNWM5MWEwN2VhYzhhYjBmNmI=',
    'request_token':'http://api.getglue.com/oauth/request_token',
    'access_token' :'http://api.getglue.com/oauth/access_token',
    'authorization':'http://getglue.com/oauth/authorize',
    'post': 'http://api.getglue.com/v2/user/addCheckin?',
    'call_back':None,
    'maxlen':140,
}

class AddAccountRequest():
    def __init__(self):
        self.api=None
        self.type=None
        
        self.request_token=None
        self.alias=None

        
    def __del__(self):
        pass

        
    def request_set_type(self, t):
        self.type=t
        
    def authorize(self, *args):
        set_hint, button, assistant, page, proxy_info=args
        
        self.pin=''

        button.set_sensitive(False)
           
        if self.type=='identica':
            api=IDENTICA
        elif self.type=='twitter':
            api=TWITTER
        elif self.type=='getglue':
            api=GETGLUE

        self.api=api            
        
        self.consumer=oauth.Consumer(decode(api['key']), decode(api['secret']))
        client=oauth.Client(self.consumer, proxy_info=proxy_info)
           
        try:     
            resp, content = client.request(api['request_token'], "GET",
                                           call_back=api['call_back'])
        except Exception as err:
            set_hint('ERR: %s' % err)
            button.set_sensitive(True)
            return
        
        if resp['status'] != '200':
            set_hint('ERR: %s' % (resp['status']))
            button.set_sensitive(True)
            return
        
        self.request_token=dict(urlparse.parse_qsl(content))
        
        
        url = "%s?oauth_token=%s" % (self.api['authorization'] , self.request_token['oauth_token'])
        set_hint('Opening your web browser')
        print url
        webbrowser.open_new(url)
        
        page[4]=True
        assistant.set_page_complete(page[0], page[4])

    def exchange(self, *args):
        set_hint, button, assistant, page, proxy_info=args
        
        button.set_sensitive(False)
        token=oauth.Token(self.request_token['oauth_token'],
                          self.request_token['oauth_token_secret'])
        token.set_verifier(self.pin)
        client = oauth.Client(self.consumer, token, proxy_info=proxy_info)
        
        try:
            resp, content = client.request(self.api['access_token'], "POST")
        except Exception as err:
            set_hint('ERR: %s' % err)
            button.set_sensitive(True)
            return
        
        if resp['status'] != '200':
            set_hint('ERR: %s\n%s' % (resp['status'], content))
            button.set_sensitive(True)
            return
        
        access_token = dict(urlparse.parse_qsl(content))

        self.access_token = access_token['oauth_token']
        self.access_token_secret = access_token['oauth_token_secret']
        
        set_hint('Done!\nnow you can forward to next page')
        
        page[4]=True
        assistant.set_page_complete(page[0], page[4])
    
    def save_account(self, mb):
        mb.settings.add_account(
                type=self.type,
                alias=self.alias,
                token=encode(self.access_token),
                token_secret=encode(self.access_token_secret),
                url='',
                maxlen=self.api['maxlen'])

class Post:
    def __init__(self, mb):
        self.mb=mb
        
    def post(self, *args):
        ui, self.artist, self.title, self.album, alias, proxy_info=args
        
        conf=self.mb.get_conf('a', alias)
        
        if conf['type']=='twitter':
            api=TWITTER
        elif conf['type']=='identica':
            api=IDENTICA
        elif conf['type']=='getglue':
            api=GETGLUE
        
        get=ui.get_object
        self.get=get
        
        w=get('general')
        w.set_sensitive(False)
        
        w=get('entry')
        text=w.get_text()

        if len(text)==0:
            self._get_out()
            return
            
        consumer = oauth.Consumer(decode(api['key']), decode(api['secret']))
        token = oauth.Token(decode(conf['token_key']), decode(conf['token_secret']))
        client = oauth.Client(consumer, token, proxy_info=proxy_info)

        if api == GETGLUE:
            params={
                'app':"Rhythmbox",
                'source':"https://github.com/aliva/rhythmbox-microblogger",
                'objectId':'recording_artists/'+self.artist.lower().replace(' ', '_'),
                'comment':(self.title+" from "+self.album)[:140]
            }
        else:
            params={
                'status':text
            }

        link=api['post']+urllib.urlencode(params)
        e=False

        try:
            resp, content = client.request(link, 'GET')
        except Exception as err:
            try:
                w=get('alias')
                w.set_text('Err: %s' % err)
                self._get_out()
                e=True
            except UnboundLocalError:
                pass

        if e:
            return
       
        if resp['status'] != '200':
            w=get('alias')
            if api==GETGLUE:
                doc=libxml2.parseDoc(content)
                code=doc.xpathEval("/adaptiveblue/error/code")[0].content
                if code=='302':
                    err='Artist not found'
                else:
                    err=code
            else:
                err=resp['status']
            w.set_text(' ERR: %s' % err)
            self._get_out()
            return

        notif=pynotify.Notification('Message sent to %s' % conf['alias'],
                                    'rbmb',
                                    self.mb.find_file('icon/%s.png' % conf['type']))
        notif.show()
        
        w=get('general')
        w.hide_all()

    def _get_out(self):
        self.get('general').set_sensitive(True)
        self.mb.sending=False
        

def decode(string):
    return base64.b64decode(string)
    
def encode(string):
    return base64.b64encode(string)

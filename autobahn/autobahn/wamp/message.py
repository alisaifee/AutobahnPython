###############################################################################
##
##  Copyright (C) 2013-2014 Tavendo GmbH
##
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##
##      http://www.apache.org/licenses/LICENSE-2.0
##
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language governing permissions and
##  limitations under the License.
##
###############################################################################

from __future__ import absolute_import

__all__ = ['Error',
           'Subscribe',
           'Subscribed',
           'Unsubscribe',
           'Unsubscribed',
           'Publish',
           'Published',
           'Event',
           'Register',
           'Registered',
           'Unregister',
           'Unregistered',
           'Call',
           'Cancel',
           'Result',
           'Invocation',
           'Interrupt',
           'Yield',
           'Hello',
           'Goodbye',
           'Heartbeat']


import json, types
from zope.interface import implementer

import autobahn
from autobahn import util
from autobahn.wamp.exception import ProtocolError
from autobahn.wamp.interfaces import IMessage



def check_or_raise_uri(value, message):
   if type(value) not in [str, unicode]:
      raise ProtocolError("{}: invalid type {} for URI".format(message, type(value)))
   if len(value) == 0:
      raise ProtocolError("{}: invalid value '{}' for URI".format(message, value))
   return value



def check_or_raise_id(value, message):
   if type(value) not in [int, long]:
      raise ProtocolError("{}: invalid type {} for ID".format(message, type(value)))
   if value < 0 or value > 9007199254740992: # 2**53
      raise ProtocolError("{}: invalid value {} for ID".format(message, value))
   return value



def check_or_raise_extra(value, message):
   if type(value) != dict:
      raise ProtocolError("{}: invalid type {}".format(message, type(value)))
   for k in value.keys():
      if type(k) not in (str, unicode):
         raise ProtocolError("{}: invalid type {} for key '{}'".format(type(k), k))
   return value



class Message(util.EqualityMixin):
   """
   WAMP message base class. This is not supposed to be instantiated.
   """

   def __init__(self):
      """
      Base constructor.
      """
      ## serialization cache: mapping from ISerializer instances
      ## to serialized bytes
      ##
      self._serialized = {}


   def uncache(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.uncache`
      """
      self._serialized = {}


   def serialize(self, serializer):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.serialize`
      """
      ## only serialize if not cached ..
      if not self._serialized.has_key(serializer):
         self._serialized[serializer] = serializer.serialize(self.marshal())
      return self._serialized[serializer]



@implementer(IMessage)
class Error(Message):
   """
   A WAMP `ERROR` message.

   Formats:
     * `[ERROR, Session|id, REQUEST.Type|int, REQUEST.Request|id, Details|dict, Error|uri]`
     * `[ERROR, Session|id, REQUEST.Type|int, REQUEST.Request|id, Details|dict, Error|uri, Arguments|list]`
     * `[ERROR, Session|id, REQUEST.Type|int, REQUEST.Request|id, Details|dict, Error|uri, Arguments|list, ArgumentsKw|dict]`
   """

   MESSAGE_TYPE = 4
   """
   The WAMP message code for this type of message.
   """


   def __init__(self, session, request_type, request, error, args = None, kwargs = None):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param request_type: The WAMP message type code for the original request.
      :type request_type: int
      :param request: The WAMP request ID of the original request (`Call`, `Subscribe`, ...) this error occured for.
      :type request: int
      :param error: The WAMP or application error URI for the error that occured.
      :type error: str
      :param args: Positional values for application-defined exception.
                   Must be serializable using any serializers in use.
      :type args: list
      :param kwargs: Keyword values for application-defined exception.
                     Must be serializable using any serializers in use.
      :type kwargs: dict
      """
      Message.__init__(self)
      self.session = session
      self.request_type = request_type
      self.request = request
      self.error = error
      self.args = args
      self.kwargs = kwargs


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Error.MESSAGE_TYPE)

      if len(wmsg) not in (6, 7, 8):
         raise ProtocolError("invalid message length {} for ERROR".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in ERROR")

      request_type = wmsg[2]
      if type(request_type) not in [int, long]:
         raise ProtocolError("invalid type {} for 'request_type' in ERROR".format(request_type))

      if request_type not in [Subscribe.MESSAGE_TYPE,
                              Unsubscribe.MESSAGE_TYPE,
                              Publish.MESSAGE_TYPE,
                              Register.MESSAGE_TYPE,
                              Unregister.MESSAGE_TYPE,
                              Call.MESSAGE_TYPE,
                              Invocation.MESSAGE_TYPE]:
         raise ProtocolError("invalid value {} for 'request_type' in ERROR".format(request_type))

      request = check_or_raise_id(wmsg[3], "'request' in ERROR")
      details = check_or_raise_extra(wmsg[4], "'details' in ERROR")
      error = check_or_raise_uri(wmsg[5], "'error' in ERROR")

      args = None
      if len(wmsg) > 6:
         args = wmsg[6]
         if type(args) != list:
            raise ProtocolError("invalid type {} for 'args' in ERROR".format(type(args)))

      kwargs = None
      if len(wmsg) > 7:
         kwargs = wmsg[7]
         if type(kwargs) != dict:
            raise ProtocolError("invalid type {} for 'kwargs' in ERROR".format(type(kwargs)))

      obj = Error(session, request_type, request, error, args = args, kwargs = kwargs)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      details = {}

      if self.kwargs:
         return [self.MESSAGE_TYPE, self.session, self.request_type, self.request, details, self.error, self.args, self.kwargs]
      elif self.args:
         return [self.MESSAGE_TYPE, self.session, self.request_type, self.request, details, self.error, self.args]
      else:
         return [self.MESSAGE_TYPE, self.session, self.request_type, self.request, details, self.error]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP Error Message (session = {}, request_type = {}, request = {}, error = {}, args = {}, kwargs = {})".format(self.session, self.request_type, self.request, self.error, self.args, self.kwargs)



@implementer(IMessage)
class Subscribe(Message):
   """
   A WAMP `SUBSCRIBE` message.

   Format: `[SUBSCRIBE, Session|id, Request|id, Options|dict, Topic|uri]`
   """

   MESSAGE_TYPE = 32
   """
   The WAMP message code for this type of message.
   """

   MATCH_EXACT = 'exact'
   MATCH_PREFIX = 'prefix'
   MATCH_WILDCARD = 'wildcard'

   def __init__(self, session, request, topic, match = MATCH_EXACT):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param request: The WAMP request ID of this request.
      :type request: int
      :param topic: The WAMP or application URI of the PubSub topic to subscribe to.
      :type topic: str
      :param match: The topic matching method to be used for the subscription.
      :type match: str
      """
      Message.__init__(self)
      self.session = session
      self.request = request
      self.topic = topic
      self.match = match


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Subscribe.MESSAGE_TYPE)

      if len(wmsg) != 5:
         raise ProtocolError("invalid message length {} for SUBSCRIBE".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in SUBSCRIBE")
      request = check_or_raise_id(wmsg[2], "'request' in SUBSCRIBE")
      options = check_or_raise_extra(wmsg[3], "'options' in SUBSCRIBE")
      topic = check_or_raise_uri(wmsg[4], "'topic' in SUBSCRIBE")

      match = Subscribe.MATCH_EXACT

      if options.has_key('match'):

         option_match = options['match']
         if type(option_match) not in [str, unicode]:
            raise ProtocolError("invalid type {} for 'match' option in SUBSCRIBE".format(type(option_match)))

         if option_match not in [Subscribe.MATCH_EXACT, Subscribe.MATCH_PREFIX, Subscribe.MATCH_WILDCARD]:
            raise ProtocolError("invalid value {} for 'match' option in SUBSCRIBE".format(option_match))

         match = option_match

      obj = Subscribe(session, request, topic, match)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      options = {}

      if self.match and self.match != Subscribe.MATCH_EXACT:
         options['match'] = self.match

      return [Subscribe.MESSAGE_TYPE, self.session, self.request, options, self.topic]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP SUBSCRIBE Message (session = {}, request = {}, topic = {}, match = {})".format(self.session, self.request, self.topic, self.match)



@implementer(IMessage)
class Subscribed(Message):
   """
   A WAMP `SUBSCRIBED` message.

   Format: `[SUBSCRIBED, Session|id, SUBSCRIBE.Request|id, Subscription|id]`
   """

   MESSAGE_TYPE = 33
   """
   The WAMP message code for this type of message.
   """

   def __init__(self, session, request, subscription):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param request: The request ID of the original `SUBSCRIBE` request.
      :type request: int
      :param subscription: The subscription ID for the subscribed topic (or topic pattern).
      :type subscription: int
      """
      Message.__init__(self)
      self.session = session
      self.request = request
      self.subscription = subscription


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Subscribed.MESSAGE_TYPE)

      if len(wmsg) != 4:
         raise ProtocolError("invalid message length {} for SUBSCRIBED".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in SUBSCRIBED")
      request = check_or_raise_id(wmsg[2], "'request' in SUBSCRIBED")
      subscription = check_or_raise_id(wmsg[3], "'subscription' in SUBSCRIBED")

      obj = Subscribed(session, request, subscription)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      return [Subscribed.MESSAGE_TYPE, self.session, self.request, self.subscription]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP SUBSCRIBED Message (session = {}, request = {}, subscription = {})".format(self.session, self.request, self.subscription)



@implementer(IMessage)
class Unsubscribe(Message):
   """
   A WAMP `UNSUBSCRIBE` message.

   Format: `[UNSUBSCRIBE, Session|id, Request|id, SUBSCRIBED.Subscription|id]`
   """

   MESSAGE_TYPE = 34
   """
   The WAMP message code for this type of message.
   """


   def __init__(self, request, subscription):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param request: The WAMP request ID of this request.
      :type request: int
      :param subscription: The subscription ID for the subscription to unsubscribe from.
      :type subscription: int
      """
      Message.__init__(self)
      self.session = session
      self.request = request
      self.subscription = subscription


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Unsubscribe.MESSAGE_TYPE)

      if len(wmsg) != 4:
         raise ProtocolError("invalid message length {} for WAMP UNSUBSCRIBE".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in UNSUBSCRIBE")
      request = check_or_raise_id(wmsg[2], "'request' in UNSUBSCRIBE")
      subscription = check_or_raise_id(wmsg[3], "'subscription' in UNSUBSCRIBE")

      obj = Unsubscribe(session, request, subscription)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      return [Unsubscribe.MESSAGE_TYPE, self.session, self.request, self.subscription]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP UNSUBSCRIBE Message (session = {}, request = {}, subscription = {})".format(self.session, self.request, self.subscription)



@implementer(IMessage)
class Unsubscribed(Message):
   """
   A WAMP `UNSUBSCRIBED` message.

   Format: `[UNSUBSCRIBED, Session|id, UNSUBSCRIBE.Request|id]`
   """

   MESSAGE_TYPE = 35
   """
   The WAMP message code for this type of message.
   """

   def __init__(self, session, request):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param request: The request ID of the original `UNSUBSCRIBE` request.
      :type request: int
      """
      Message.__init__(self)
      self.session = session
      self.request = request


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Unsubscribed.MESSAGE_TYPE)

      if len(wmsg) != 3:
         raise ProtocolError("invalid message length {} for UNSUBSCRIBED".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in UNSUBSCRIBED")
      request = check_or_raise_id(wmsg[2], "'request' in UNSUBSCRIBED")

      obj = Unsubscribed(session, request)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      return [Unsubscribed.MESSAGE_TYPE, self.session, self.request]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP UNSUBSCRIBED Message (session = {}, request = {})".format(self.session, self.request)



@implementer(IMessage)
class Publish(Message):
   """
   A WAMP `PUBLISH` message.

   Formats:
     * `[PUBLISH, Session|id, Request|id, Options|dict, Topic|uri]`
     * `[PUBLISH, Session|id, Request|id, Options|dict, Topic|uri, Arguments|list]`
     * `[PUBLISH, Session|id, Request|id, Options|dict, Topic|uri, Arguments|list, ArgumentsKw|dict]`
   """

   MESSAGE_TYPE = 16
   """
   The WAMP message code for this type of message.
   """

   def __init__(self,
                session,
                request,
                topic,
                args = None,
                kwargs = None,
                acknowledge = None,
                excludeMe = None,
                exclude = None,
                eligible = None,
                discloseMe = None):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param request: The WAMP request ID of this request.
      :type request: int
      :param topic: The WAMP or application URI of the PubSub topic the event should
                    be published to.
      :type topic: str
      :param args: Positional values for application-defined event payload.
                   Must be serializable using any serializers in use.
      :type args: list
      :param kwargs: Keyword values for application-defined event payload.
                     Must be serializable using any serializers in use.
      :type kwargs: dict
      :param acknowledge: If True, acknowledge the publication with a success or
                          error response.
      :type acknowledge: bool
      :param excludeMe: If True, exclude the publisher from receiving the event, even
                        if he is subscribed (and eligible).
      :type excludeMe: bool
      :param exclude: List of WAMP session IDs to exclude from receiving this event.
      :type exclude: list
      :param eligible: List of WAMP session IDs eligible to receive this event.
      :type eligible: list
      :param discloseMe: If True, request to disclose the publisher of this event
                         to subscribers.
      :type discloseMe: bool
      """
      assert(not (kwargs and not args))
      Message.__init__(self)
      self.session = session
      self.request = request
      self.topic = topic
      self.args = args
      self.kwargs = kwargs
      self.acknowledge = acknowledge
      self.excludeMe = excludeMe
      self.exclude = exclude
      self.eligible = eligible
      self.discloseMe = discloseMe


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Publish.MESSAGE_TYPE)

      if len(wmsg) not in (5, 6, 7):
         raise ProtocolError("invalid message length {} for PUBLISH".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in PUBLISH")
      request = check_or_raise_id(wmsg[2], "'request' in PUBLISH")
      options = check_or_raise_extra(wmsg[3], "'options' in PUBLISH")
      topic = check_or_raise_uri(wmsg[4], "'topic' in PUBLISH")

      args = None
      if len(wmsg) > 5:
         args = wmsg[5]
         if type(args) != list:
            raise ProtocolError("invalid type {} for 'args' in PUBLISH".format(type(args)))

      kwargs = None
      if len(wmsg) > 6:
         kwargs = wmsg[6]
         if type(kwargs) != dict:
            raise ProtocolError("invalid type {} for 'kwargs' in PUBLISH".format(type(kwargs)))

      acknowledge = None
      excludeMe = None
      exclude = None
      eligible = None
      discloseMe = None

      if options.has_key('acknowledge'):

         option_acknowledge = options['acknowledge']
         if type(option_acknowledge) != bool:
            raise ProtocolError("invalid type {} for 'acknowledge' option in PUBLISH".format(type(option_acknowledge)))

         acknowledge = option_acknowledge

      if options.has_key('excludeme'):

         option_excludeMe = options['excludeme']
         if type(option_excludeMe) != bool:
            raise ProtocolError("invalid type {} for 'excludeme' option in PUBLISH".format(type(option_excludeMe)))

         excludeMe = option_excludeMe

      if options.has_key('exclude'):

         option_exclude = options['exclude']
         if type(option_exclude) != list:
            raise ProtocolError("invalid type {} for 'exclude' option in PUBLISH".format(type(option_exclude)))

         for sessionId in option_exclude:
            if type(sessionId) not in [int, long]:
               raise ProtocolError("invalid type {} for value in 'exclude' option in PUBLISH".format(type(sessionId)))

         exclude = option_exclude

      if options.has_key('eligible'):

         option_eligible = options['eligible']
         if type(option_eligible) != list:
            raise ProtocolError("invalid type {} for 'eligible' option in PUBLISH".format(type(option_eligible)))

         for sessionId in option_eligible:
            if type(sessionId) not in [int, long]:
               raise ProtocolError("invalid type {} for value in 'eligible' option in PUBLISH".format(type(sessionId)))

         eligible = option_eligible

      if options.has_key('discloseme'):

         option_discloseMe = options['discloseme']
         if type(option_discloseMe) != bool:
            raise ProtocolError("invalid type {} for 'discloseme' option in PUBLISH".format(type(option_identifyMe)))

         discloseMe = option_discloseMe

      obj = Publish(session,
                    request,
                    topic,
                    args = args,
                    kwargs = kwargs,
                    acknowledge = acknowledge,
                    excludeMe = excludeMe,
                    exclude = exclude,
                    eligible = eligible,
                    discloseMe = discloseMe)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      options = {}

      if self.acknowledge is not None:
         options['acknowledge'] = self.acknowledge
      if self.excludeMe is not None:
         options['excludeme'] = self.excludeMe
      if self.exclude is not None:
         options['exclude'] = self.exclude
      if self.eligible is not None:
         options['eligible'] = self.eligible
      if self.discloseMe is not None:
         options['discloseme'] = self.discloseMe

      if self.kwargs:
         return [Publish.MESSAGE_TYPE, self.session, self.request, options, self.topic, self.args, self.kwargs]
      elif self.args:
         return [Publish.MESSAGE_TYPE, self.session, self.request, options, self.topic, self.args]
      else:
         return [Publish.MESSAGE_TYPE, self.session, self.request, options, self.topic]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP PUBLISH Message (session = {}, request = {}, topic = {}, args = {}, kwargs = {}, acknowledge = {}, excludeMe = {}, exclude = {}, eligible = {}, discloseMe = {})".format(self.session, self.request, self.topic, self.args, self.kwargs, self.acknowledge, self.excludeMe, self.exclude, self.eligible, self.discloseMe)



@implementer(IMessage)
class Published(Message):
   """
   A WAMP `PUBLISHED` message.

   Format: `[PUBLISHED, Session|id, PUBLISH.Request|id, Publication|id]`
   """

   MESSAGE_TYPE = 17
   """
   The WAMP message code for this type of message.
   """

   def __init__(self, session, request, publication):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param request: The request ID of the original `PUBLISH` request.
      :type request: int
      :param publication: The publication ID for the published event.
      :type publication: int
      """
      Message.__init__(self)
      self.session = session
      self.request = request
      self.publication = publication


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Published.MESSAGE_TYPE)

      if len(wmsg) != 4:
         raise ProtocolError("invalid message length {} for PUBLISHED".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in PUBLISHED")
      request = check_or_raise_id(wmsg[2], "'request' in PUBLISHED")
      publication = check_or_raise_id(wmsg[3], "'publication' in PUBLISHED")

      obj = Published(session, request, publication)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      return [Published.MESSAGE_TYPE, self.session, self.request, self.publication]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP PUBLISHED Message (session = {}, request = {}, publication = {})".format(self.session, self.request, self.publication)



@implementer(IMessage)
class Event(Message):
   """
   A WAMP `EVENT` message.

   Formats:

     * `[EVENT, Session|id, SUBSCRIBED.Subscription|id, PUBLISHED.Publication|id, Details|dict]`
     * `[EVENT, Session|id, SUBSCRIBED.Subscription|id, PUBLISHED.Publication|id, Details|dict, PUBLISH.Arguments|list]`
     * `[EVENT, Session|id, SUBSCRIBED.Subscription|id, PUBLISHED.Publication|id, Details|dict, PUBLISH.Arguments|list, PUBLISH.ArgumentsKw|dict]`
   """

   MESSAGE_TYPE = 36
   """
   The WAMP message code for this type of message.
   """


   def __init__(self, session, subscription, publication, args = None, kwargs = None, publisher = None):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param subscription: The subscription ID this event is dispatched under.
      :type subscription: int
      :param publication: The publication ID of the dispatched event.
      :type publication: int
      :param args: Positional values for application-defined exception.
                   Must be serializable using any serializers in use.
      :type args: list
      :param kwargs: Keyword values for application-defined exception.
                     Must be serializable using any serializers in use.
      :type kwargs: dict
      :param publisher: If present, the WAMP session ID of the publisher of this event.
      :type publisher: str
      """
      assert(not (kwargs and not args))
      Message.__init__(self)
      self.session = session
      self.subscription = subscription
      self.publication = publication
      self.args = args
      self.kwargs = kwargs
      self.publisher = publisher


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Event.MESSAGE_TYPE)

      if len(wmsg) not in (5, 6, 7):
         raise ProtocolError("invalid message length {} for EVENT".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in EVENT")
      subscription = check_or_raise_id(wmsg[2], "'subscription' in EVENT")
      publication = check_or_raise_id(wmsg[3], "'publication' in EVENT")
      details = check_or_raise_extra(wmsg[4], "'details' in EVENT")

      args = None
      if len(wmsg) > 5:
         args = wmsg[5]
         if type(args) != list:
            raise ProtocolError("invalid type {} for 'args' in EVENT".format(type(args)))

      kwargs = None
      if len(wmsg) > 6:
         kwargs = wmsg[6]
         if type(kwargs) != dict:
            raise ProtocolError("invalid type {} for 'kwargs' in EVENT".format(type(kwargs)))

      publisher = None
      if details.has_key('publisher'):

         detail_publisher = details['publisher']
         if type(detail_publisher) not in [int, long]:
            raise ProtocolError("invalid type {} for 'publisher' detail in EVENT".format(type(detail_publisher)))

         publisher = detail_publisher

      obj = Event(session,
                  subscription,
                  publication,
                  args = args,
                  kwargs = kwargs,
                  publisher = publisher)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      details = {}

      if self.publisher is not None:
         details['publisher'] = self.publisher

      if self.kwargs:
         return [Event.MESSAGE_TYPE, self.session, self.subscription, self.publication, details, self.args, self.kwargs]
      elif self.args:
         return [Event.MESSAGE_TYPE, self.session, self.subscription, self.publication, details, self.args]
      else:
         return [Event.MESSAGE_TYPE, self.session, self.subscription, self.publication, details]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP EVENT Message (session = {}, subscription = {}, publication = {}, args = {}, kwargs = {}, publisher = {})".format(self.session, self.subscription, self.publication, self.args, self.kwargs, self.publisher)



@implementer(IMessage)
class Register(Message):
   """
   A WAMP `REGISTER` message.

   Format: `[REGISTER, Session|id, Request|id, Options|dict, Procedure|uri]`
   """

   MESSAGE_TYPE = 64
   """
   The WAMP message code for this type of message.
   """

   def __init__(self, session, request, procedure, pkeys = None):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param request: The WAMP request ID of this request.
      :type request: int
      :param procedure: The WAMP or application URI of the RPC endpoint provided.
      :type procedure: str
      :param pkeys: The endpoint can work for this list of application partition keys.
      :type pkeys: list
      """
      Message.__init__(self)
      self.session = session
      self.request = request
      self.procedure = procedure
      self.pkeys = pkeys


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Register.MESSAGE_TYPE)

      if len(wmsg) != 5:
         raise ProtocolError("invalid message length {} for REGISTER".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in REGISTER")
      request = check_or_raise_id(wmsg[2], "'request' in REGISTER")
      options = check_or_raise_extra(wmsg[3], "'options' in REGISTER")
      procedure = check_or_raise_uri(wmsg[4], "'procedure' in REGISTER")

      pkeys = None

      if options.has_key('pkeys'):

         option_pkeys = options['pkeys']
         if type(option_pkeys) != list:
            raise ProtocolError("invalid type {} for 'pkeys' option in REGISTER".format(type(option_pkeys)))

         for pk in option_pkeys:
            if type(pk) not in [int, long]:
               raise ProtocolError("invalid type for value '{}' in 'pkeys' option in REGISTER".format(type(pk)))

         pkeys = option_pkeys

      obj = Register(session, request, procedure, pkeys = pkeys)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      options = {}

      if self.pkeys is not None:
         options['pkeys'] = self.pkeys

      return [Register.MESSAGE_TYPE, self.session, self.request, options, self.procedure]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP REGISTER Message (session = {}, request = {}, procedure = {}, pkeys = {})".format(self.session, self.request, self.procedure, self.pkeys)



@implementer(IMessage)
class Registered(Message):
   """
   A WAMP `REGISTERED` message.

   Format: `[REGISTERED, Session|id, REGISTER.Request|id, Registration|id]`
   """

   MESSAGE_TYPE = 65
   """
   The WAMP message code for this type of message.
   """

   def __init__(self, session, request, registration):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param request: The request ID of the original `REGISTER` request.
      :type request: int
      :param subscription: The registration ID for the registered procedure (or procedure pattern).
      :type subscription: int
      """
      Message.__init__(self)
      self.session = session
      self.request = request
      self.registration = registration


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Registered.MESSAGE_TYPE)

      if len(wmsg) != 4:
         raise ProtocolError("invalid message length {} for REGISTERED".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in REGISTERED")
      request = check_or_raise_id(wmsg[2], "'request' in REGISTERED")
      registration = check_or_raise_id(wmsg[3], "'registration' in REGISTERED")

      obj = Registered(session, request, registration)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      return [Registered.MESSAGE_TYPE, self.session, self.request, self.registration]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP REGISTERED Message (session = {}, request = {}, registration = {})".format(self.session, self.request, self.registration)



@implementer(IMessage)
class Unregister(Message):
   """
   A WAMP Unprovide message.

   Format: `[UNREGISTER, Session|id, Request|id, REGISTERED.Registration|id]`
   """

   MESSAGE_TYPE = 66
   """
   The WAMP message code for this type of message.
   """


   def __init__(self, session, request, registration):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param request: The WAMP request ID of this request.
      :type request: int
      :param registration: The registration ID for the registration to unregister.
      :type registration: int
      """
      Message.__init__(self)
      self.session = session
      self.request = request
      self.registration = registration


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Unregister.MESSAGE_TYPE)

      if len(wmsg) != 4:
         raise ProtocolError("invalid message length {} for WAMP UNREGISTER".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in UNREGISTER")
      request = check_or_raise_id(wmsg[2], "'request' in UNREGISTER")
      registration = check_or_raise_id(wmsg[3], "'registration' in UNREGISTER")

      obj = Unregister(session, request, registration)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      return [Unregister.MESSAGE_TYPE, self.session, self.request, self.registration]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP UNREGISTER Message (session = {}, request = {}, registration = {})".format(self.session, self.request, self.registration)



@implementer(IMessage)
class Unregistered(Message):
   """
   A WAMP `UNREGISTERED` message.

   Format: `[UNREGISTERED, Session|id, UNREGISTER.Request|id]`
   """

   MESSAGE_TYPE = 67
   """
   The WAMP message code for this type of message.
   """

   def __init__(self, session, request):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param request: The request ID of the original `UNREGISTER` request.
      :type request: int
      """
      Message.__init__(self)
      self.session = session
      self.request = request


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Unregistered.MESSAGE_TYPE)

      if len(wmsg) != 3:
         raise ProtocolError("invalid message length {} for UNREGISTER".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in UNREGISTER")
      request = check_or_raise_id(wmsg[2], "'request' in UNREGISTER")

      obj = Unregistered(request)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      return [Unregistered.MESSAGE_TYPE, self.session, self.request]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP UNREGISTER Message (session = {}, request = {})".format(self.session, self.request)



@implementer(IMessage)
class Call(Message):
   """
   A WAMP `CALL` message.

   Formats:
     * `[CALL, Session|id, Request|id, Options|dict, Procedure|uri]`
     * `[CALL, Session|id, Request|id, Options|dict, Procedure|uri, Arguments|list]`
     * `[CALL, Session|id, Request|id, Options|dict, Procedure|uri, Arguments|list, ArgumentsKw|dict]`
   """

   MESSAGE_TYPE = 48
   """
   The WAMP message code for this type of message.
   """

   def __init__(self,
                session,
                request,
                procedure,
                args = None,
                kwargs = None,
                timeout = None,
                receive_progress = None,
                discloseMe = None):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param request: The WAMP request ID of this request.
      :type request: int
      :param topic: The WAMP or application URI of the procedure which should be called.
      :type topic: str
      :param args: Positional values for application-defined call arguments.
                   Must be serializable using any serializers in use.
      :type args: list
      :param kwargs: Keyword values for application-defined call arguments.
                     Must be serializable using any serializers in use.
      :param timeout: If present, let the callee automatically cancel
                      the call after this ms.
      :type timeout: int
      """
      Message.__init__(self)
      self.session = session
      self.request = request
      self.procedure = procedure
      self.args = args
      self.kwargs = kwargs
      self.timeout = timeout
      self.receive_progress = receive_progress
      self.discloseMe = discloseMe


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Call.MESSAGE_TYPE)

      if len(wmsg) not in (5, 6, 7):
         raise ProtocolError("invalid message length {} for CALL".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in CALL")
      request = check_or_raise_id(wmsg[2], "'request' in CALL")
      options = check_or_raise_extra(wmsg[3], "'options' in CALL")
      procedure = check_or_raise_uri(wmsg[4], "'procedure' in CALL")

      args = None
      if len(wmsg) > 5:
         args = wmsg[5]
         if type(args) != list:
            raise ProtocolError("invalid type {} for 'args' in CALL".format(type(args)))

      kwargs = None
      if len(wmsg) > 6:
         kwargs = wmsg[6]
         if type(kwargs) != dict:
            raise ProtocolError("invalid type {} for 'kwargs' in CALL".format(type(kwargs)))

      timeout = None
      if options.has_key('timeout'):

         option_timeout = options['timeout']
         if type(option_timeout) not in [int, long]:
            raise ProtocolError("invalid type {} for 'timeout' option in CALL".format(type(option_timeout)))

         if option_timeout < 0:
            raise ProtocolError("invalid value {} for 'timeout' option in CALL".format(option_timeout))

         timeout = option_timeout

      receive_progress = None
      if options.has_key('receive_progress'):

         option_receive_progress = options['receive_progress']
         if type(option_receive_progress) != bool:
            raise ProtocolError("invalid type {} for 'receive_progress' option in CALL".format(type(option_receive_progress)))

         receive_progress = option_receive_progress

      discloseMe = None
      if options.has_key('discloseme'):

         option_discloseMe = options['discloseme']
         if type(option_discloseMe) != bool:
            raise ProtocolError("invalid type {} for 'discloseme' option in CALL".format(type(option_identifyMe)))

         discloseMe = option_discloseMe

      obj = Call(session,
                 request,
                 procedure,
                 args = args,
                 kwargs = kwargs,
                 timeout = timeout,
                 receive_progress = receive_progress,
                 discloseMe = discloseMe)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      options = {}

      if self.timeout is not None:
         options['timeout'] = self.timeout

      if self.receive_progress is not None:
         options['receive_progress'] = self.receive_progress

      if self.discloseMe is not None:
         options['discloseme'] = self.discloseMe

      if self.kwargs:
         return [Call.MESSAGE_TYPE, self.session, self.request, options, self.procedure, self.args, self.kwargs]
      elif self.args:
         return [Call.MESSAGE_TYPE, self.session, self.request, options, self.procedure, self.args]
      else:
         return [Call.MESSAGE_TYPE, self.session, self.request, options, self.procedure]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP CALL Message (session = {}, request = {}, procedure = {}, args = {}, kwargs = {}, timeout = {}, receive_progress = {}, discloseMe = {})".format(self.session, self.request, self.procedure, self.args, self.kwargs, self.timeout, self.receive_progress, self.discloseMe)



@implementer(IMessage)
class Cancel(Message):
   """
   A WAMP `CANCEL` message.

   Format: `[CANCEL, Session|id, CALL.Request|id, Options|dict]`
   """

   MESSAGE_TYPE = 49
   """
   The WAMP message code for this type of message.
   """

   SKIP = 'skip'
   ABORT = 'abort'
   KILL = 'kill'


   def __init__(self, session, request, mode = None):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param request: The WAMP request ID of the original `CALL` to cancel.
      :type request: int
      :param mode: Specifies how to cancel the call (skip, abort or kill).
      :type mode: str
      """
      Message.__init__(self)
      self.session = session
      self.request = request
      self.mode = mode


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Cancel.MESSAGE_TYPE)

      if len(wmsg) != 4:
         raise ProtocolError("invalid message length {} for CANCEL".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in CANCEL")
      request = check_or_raise_id(wmsg[2], "'request' in CANCEL")
      options = check_or_raise_extra(wmsg[3], "'options' in CANCEL")

      ## options
      ##
      mode = None

      if options.has_key('mode'):

         option_mode = options['mode']
         if type(option_mode) not in (str, unicode):
            raise ProtocolError("invalid type {} for 'mode' option in CANCEL".format(type(option_mode)))

         if option_mode not in [Cancel.SKIP, Cancel.ABORT, Cancel.KILL]:
            raise ProtocolError("invalid value '{}' for 'mode' option in CANCEL".format(option_mode))

         mode = option_mode

      obj = Cancel(session, request, mode = mode)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      options = {}

      if self.mode is not None:
         options['mode'] = self.mode

      return [Cancel.MESSAGE_TYPE, self.session, self.request, options]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP CANCEL Message (session = {}, request = {}, mode = '{}'')".format(self.session, self.request, self.mode)



@implementer(IMessage)
class Result(Message):
   """
   A WAMP `RESULT` message.

   Formats:
     * `[RESULT, Session|id, CALL.Request|id, Details|dict]`
     * `[RESULT, Session|id, CALL.Request|id, Details|dict, YIELD.Arguments|list]`
     * `[RESULT, Session|id, CALL.Request|id, Details|dict, YIELD.Arguments|list, YIELD.ArgumentsKw|dict]`
   """

   MESSAGE_TYPE = 50
   """
   The WAMP message code for this type of message.
   """

   def __init__(self, session, request, args = None, kwargs = None, progress = None):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param request: The request ID of the original `CALL` request.
      :type request: int
      :param args: Positional values for application-defined event payload.
                   Must be serializable using any serializers in use.
      :type args: list
      :param kwargs: Keyword values for application-defined event payload.
                     Must be serializable using any serializers in use.
      :type kwargs: dict
      :progress: If `True`, this result is a progressive call result, and subsequent
                 results (or a final error) will follow.
      """
      Message.__init__(self)
      self.session = session
      self.request = request
      self.args = args
      self.kwargs = kwargs
      self.progress = progress


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Result.MESSAGE_TYPE)

      if len(wmsg) not in (4, 5, 6):
         raise ProtocolError("invalid message length {} for RESULT".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in RESULT")
      request = check_or_raise_id(wmsg[2], "'request' in RESULT")
      details = check_or_raise_extra(wmsg[3], "'details' in RESULT")

      args = None
      if len(wmsg) > 4:
         args = wmsg[4]
         if type(args) != list:
            raise ProtocolError("invalid type {} for 'args' in RESULT".format(type(args)))

      kwargs = None
      if len(wmsg) > 5:
         kwargs = wmsg[5]
         if type(kwargs) != dict:
            raise ProtocolError("invalid type {} for 'kwargs' in RESULT".format(type(kwargs)))

      progress = None

      if details.has_key('progress'):

         detail_progress = details['progress']
         if type(detail_progress) != bool:
            raise ProtocolError("invalid type {} for 'progress' option in RESULT".format(type(detail_progress)))

         progress = detail_progress

      obj = Result(session, request, args = args, kwargs = kwargs, progress = progress)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      details = {}

      if self.progress is not None:
         details['progress'] = self.progress

      if self.kwargs:
         return [Result.MESSAGE_TYPE, self.session, self.request, details, self.args, self.kwargs]
      elif self.args:
         return [Result.MESSAGE_TYPE, self.session, self.request, details, self.args]
      else:
         return [Result.MESSAGE_TYPE, self.session, self.request, details]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP RESULT Message (session = {}, request = {}, args = {}, kwargs = {}, progress = {})".format(self.session, self.request, self.args, self.kwargs, self.progress)



@implementer(IMessage)
class Invocation(Message):
   """
   A WAMP `INVOCATION` message.

   Formats:
     * `[INVOCATION, Session|id, Request|id, REGISTERED.Registration|id, Details|dict]`
     * `[INVOCATION, Session|id, Request|id, REGISTERED.Registration|id, Details|dict, CALL.Arguments|list]`
     * `[INVOCATION, Session|id, Request|id, REGISTERED.Registration|id, Details|dict, CALL.Arguments|list, CALL.ArgumentsKw|dict]`
   """

   MESSAGE_TYPE = 68
   """
   The WAMP message code for this type of message.
   """


   def __init__(self,
                session,
                request,
                registration,
                args = None,
                kwargs = None,
                timeout = None,
                receive_progress = None,
                caller = None):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param request: The WAMP request ID of this request.
      :type request: int
      :param registration: The registration ID of the endpoint to be invoked.
      :type registration: int
      :param args: Positional values for application-defined event payload.
                   Must be serializable using any serializers in use.
      :type args: list
      :param kwargs: Keyword values for application-defined event payload.
                     Must be serializable using any serializers in use.
      :type kwargs: dict
      :param timeout: If present, let the callee automatically cancels
                      the invocation after this ms.
      :type timeout: int
      """
      Message.__init__(self)
      self.session = session
      self.request = request
      self.registration = registration
      self.args = args
      self.kwargs = kwargs
      self.timeout = timeout
      self.receive_progress = receive_progress
      self.caller = caller


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Invocation.MESSAGE_TYPE)

      if len(wmsg) not in (5, 6, 7):
         raise ProtocolError("invalid message length {} for INVOCATION".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in INVOCATION")
      request = check_or_raise_id(wmsg[2], "'request' in INVOCATION")
      registration = check_or_raise_id(wmsg[3], "'registration' in INVOCATION")
      details = check_or_raise_extra(wmsg[4], "'details' in INVOCATION")

      args = None
      if len(wmsg) > 5:
         args = wmsg[5]
         if type(args) != list:
            raise ProtocolError("invalid type {} for 'args' in INVOCATION".format(type(args)))

      kwargs = None
      if len(wmsg) > 6:
         kwargs = wmsg[6]
         if type(kwargs) != dict:
            raise ProtocolError("invalid type {} for 'kwargs' in INVOCATION".format(type(kwargs)))

      timeout = None
      if details.has_key('timeout'):

         detail_timeout = details['timeout']
         if type(detail_timeout) not in [int, long]:
            raise ProtocolError("invalid type {} for 'timeout' detail in INVOCATION".format(type(detail_timeout)))

         if detail_timeout < 0:
            raise ProtocolError("invalid value {} for 'timeout' detail in INVOCATION".format(detail_timeout))

         timeout = detail_timeout

      receive_progress = None
      if details.has_key('receive_progress'):

         detail_receive_progress = details['receive_progress']
         if type(detail_receive_progress) != bool:
            raise ProtocolError("invalid type {} for 'receive_progress' detail in INVOCATION".format(type(detail_receive_progress)))

         receive_progress = detail_receive_progress

      caller = None
      if details.has_key('caller'):

         detail_caller = details['caller']
         if type(detail_caller) not in [int, long]:
            raise ProtocolError("invalid type {} for 'caller' detail in INVOCATION".format(type(detail_caller)))

         caller = detail_caller

      obj = Invocation(session,
                       request,
                       registration,
                       args = args,
                       kwargs = kwargs,
                       timeout = timeout,
                       receive_progress = receive_progress,
                       caller = caller)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      options = {}

      if self.timeout is not None:
         options['timeout'] = self.timeout

      if self.receive_progress is not None:
         options['receive_progress'] = self.receive_progress

      if self.caller is not None:
         options['caller'] = self.caller

      if self.kwargs:
         return [Invocation.MESSAGE_TYPE, self.session, self.request, self.registration, options, self.args, self.kwargs]
      elif self.args:
         return [Invocation.MESSAGE_TYPE, self.session, self.request, self.registration, options, self.args]
      else:
         return [Invocation.MESSAGE_TYPE, self.session, self.request, self.registration, options]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP INVOCATION Message (session = {}, request = {}, registration = {}, args = {}, kwargs = {}, timeout = {}, receive_progress = {}, caller = {})".format(self.session, self.request, self.registration, self.args, self.kwargs, self.timeout, self.receive_progress, self.caller)



@implementer(IMessage)
class Interrupt(Message):
   """
   A WAMP `INTERRUPT` message.

   Format: `[INTERRUPT, Session|id, INVOCATION.Request|id, Options|dict]`
   """

   MESSAGE_TYPE = 69
   """
   The WAMP message code for this type of message.
   """

   ABORT = 'abort'
   KILL = 'kill'


   def __init__(self, session, request, mode = None):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param request: The WAMP request ID of the original `INVOCATION` to interrupt.
      :type request: int
      :param mode: Specifies how to interrupt the invocation (abort or kill).
      :type mode: str
      """
      Message.__init__(self)
      self.session = session
      self.request = request
      self.mode = mode


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Interrupt.MESSAGE_TYPE)

      if len(wmsg) != 4:
         raise ProtocolError("invalid message length {} for INTERRUPT".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in INTERRUPT")
      request = check_or_raise_id(wmsg[2], "'request' in INTERRUPT")
      options = check_or_raise_extra(wmsg[3], "'options' in INTERRUPT")

      ## options
      ##
      mode = None

      if options.has_key('mode'):

         option_mode = options['mode']
         if type(option_mode) not in (str, unicode):
            raise ProtocolError("invalid type {} for 'mode' option in INTERRUPT".format(type(option_mode)))

         if option_mode not in [Interrupt.ABORT, Interrupt.KILL]:
            raise ProtocolError("invalid value '{}' for 'mode' option in INTERRUPT".format(option_mode))

         mode = option_mode

      obj = Interrupt(session, request, mode = mode)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      options = {}

      if self.mode is not None:
         options['mode'] = self.mode

      return [Interrupt.MESSAGE_TYPE, self.session, self.request, options]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP INTERRUPT Message (session = {}, request = {}, mode = '{}'')".format(self.session, self.request, self.mode)



@implementer(IMessage)
class Yield(Message):
   """
   A WAMP `YIELD` message.

   Formats:
     * `[YIELD, Session|id, INVOCATION.Request|id, Options|dict]`
     * `[YIELD, Session|id, INVOCATION.Request|id, Options|dict, Arguments|list]`
     * `[YIELD, Session|id, INVOCATION.Request|id, Options|dict, Arguments|list, ArgumentsKw|dict]`
   """

   MESSAGE_TYPE = 70
   """
   The WAMP message code for this type of message.
   """


   def __init__(self, session, request, args = None, kwargs = None, progress = None):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param request: The WAMP request ID of the original call.
      :type request: int
      :param args: Positional values for application-defined event payload.
                   Must be serializable using any serializers in use.
      :type args: list
      :param kwargs: Keyword values for application-defined event payload.
                     Must be serializable using any serializers in use.
      :type kwargs: dict
      :progress: If `True`, this result is a progressive invocation result, and subsequent
                 results (or a final error) will follow.
      """
      Message.__init__(self)
      self.session = session
      self.request = request
      self.args = args
      self.kwargs = kwargs
      self.progress = progress


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Yield.MESSAGE_TYPE)

      if len(wmsg) not in (4, 5, 6):
         raise ProtocolError("invalid message length {} for YIELD".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in YIELD")
      request = check_or_raise_id(wmsg[2], "'request' in YIELD")
      options = check_or_raise_extra(wmsg[3], "'options' in YIELD")

      args = None
      if len(wmsg) > 4:
         args = wmsg[4]
         if type(args) != list:
            raise ProtocolError("invalid type {} for 'args' in YIELD".format(type(args)))

      kwargs = None
      if len(wmsg) > 5:
         kwargs = wmsg[5]
         if type(kwargs) != dict:
            raise ProtocolError("invalid type {} for 'kwargs' in YIELD".format(type(kwargs)))

      progress = None

      if options.has_key('progress'):

         option_progress = options['progress']
         if type(option_progress) != bool:
            raise ProtocolError("invalid type {} for 'progress' option in YIELD".format(type(option_progress)))

         progress = option_progress

      obj = Yield(session, request, args = args, kwargs = kwargs, progress = progress)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      options = {}

      if self.progress is not None:
         options['progress'] = self.progress

      if self.kwargs:
         return [Yield.MESSAGE_TYPE, self.session, self.request, options, self.args, self.kwargs]
      elif self.args:
         return [Yield.MESSAGE_TYPE, self.session, self.request, options, self.args]
      else:
         return [Yield.MESSAGE_TYPE, self.session, self.request, options]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP YIELD Message (session = {}, request = {}, args = {}, kwargs = {}, progress = {})".format(self.session, self.request, self.args, self.kwargs, self.progress)



@implementer(IMessage)
class Hello(Message):
   """
   A WAMP `HELLO` message.

   Format: `[HELLO, Session|id, Realm|uri, Details|dict]`
   """

   MESSAGE_TYPE = 1
   """
   The WAMP message code for this type of message.
   """


   def __init__(self, session, realm, roles):
      """
      Message constructor.

      :param session: The WAMP session ID the other peer is assigned.
      :type session: int
      """
      for role in roles:
         assert(isinstance(role, autobahn.wamp.role.RoleFeatures))
      Message.__init__(self)
      self.session = session
      self.realm = realm
      self.roles = roles


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Hello.MESSAGE_TYPE)

      if len(wmsg) != 4:
         raise ProtocolError("invalid message length {} for HELLO".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in HELLO")
      realm = check_or_raise_uri(wmsg[2], "'realm' in HELLO")
      details = check_or_raise_extra(wmsg[3], "'details' in HELLO")

      roles = []

      if not details.has_key('roles'):
         raise ProtocolError("missing mandatory roles attribute in options in HELLO")

      details_roles = check_or_raise_extra(details['roles'], "'roles' in 'details' in HELLO")

      if len(details_roles) == 0:
         raise ProtocolError("empty 'roles' in 'details' in HELLO")

      for role in details_roles:
         if role not in autobahn.wamp.role.ROLE_NAME_TO_CLASS:
            raise ProtocolError("invalid role '{}' in 'roles' in 'details' in HELLO".format(role))

         if details_roles[role].has_key('features'):
            details_role_features = check_or_raise_extra(details_roles[role]['features'], "'features' in role '{}' in 'roles' in 'details' in HELLO".format(role))

            ## FIXME: skip unknown attributes
            role_features = autobahn.wamp.role.ROLE_NAME_TO_CLASS[role](**details_roles[role]['features'])

         else:
            role_features = autobahn.wamp.role.ROLE_NAME_TO_CLASS[role]()

         roles.append(role_features)

      obj = Hello(session, realm, roles)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      details = {'roles': {}}
      for role in self.roles:
         details['roles'][role.ROLE] = {}
         for feature in role.__dict__:
            if not feature.startswith('_') and feature != 'ROLE' and getattr(role, feature) is not None:
               if not details['roles'][role.ROLE].has_key('features'):
                  details['roles'][role.ROLE] = {'features': {}}
               details['roles'][role.ROLE]['features'][feature] = getattr(role, feature)

      return [Hello.MESSAGE_TYPE, self.session, self.realm, details]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP HELLO Message (session = {}, realm = {}, roles = {})".format(self.session, self.realm, self.roles)



@implementer(IMessage)
class Goodbye(Message):
   """
   A WAMP `GOODBYE` message.

   Format: `[GOODBYE, Session|id, Details|dict]`
   """

   MESSAGE_TYPE = 2
   """
   The WAMP message code for this type of message.
   """


   def __init__(self, session, reason = None, message = None):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param reason: Optional WAMP or application URI for closing reason.
      :type reason: str
      :param message: Optional human-readable closing message, e.g. for logging purposes.
      :type message: str
      """
      Message.__init__(self)
      self.session = session
      self.reason = reason
      self.message = message


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Goodbye.MESSAGE_TYPE)

      if len(wmsg) != 3:
         raise ProtocolError("invalid message length {} for GOODBYE".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in GOODBYE")
      details = check_or_raise_extra(wmsg[2], "'details' in GOODBYE")

      reason = None
      message = None

      if details.has_key('reason'):
         reason = check_or_raise_uri(details['reason'], "'reason' detail in GOODBYE")

      if details.has_key('message'):

         details_message = details['message']
         if type(details_message) not in [str, unicode]:
            raise ProtocolError("invalid type {} for 'message' detail in GOODBYE".format(type(details_message)))

         message = details_message

      obj = Goodbye(session, reason, message)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      details = {}
      if self.reason:
         details['reason'] = self.reason
      if self.message:
         details['message'] = self.message

      return [Goodbye.MESSAGE_TYPE, self.session, details]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP GOODBYE Message (session = {}, reason = {}, message = {})".format(self.session, self.reason, self.message)



@implementer(IMessage)
class Heartbeat(Message):
   """
   A WAMP `HEARTBEAT` message.

   Formats:

     * `[HEARTBEAT, Session|id, Incoming|integer, Outgoing|integer]`
     * `[HEARTBEAT, Session|id, Incoming|integer, Outgoing|integer, Discard|string]`
   """

   MESSAGE_TYPE = 3
   """
   The WAMP message code for this type of message.
   """


   def __init__(self, session, incoming, outgoing, discard = None):
      """
      Message constructor.

      :param session: The WAMP session ID this message is transported for.
      :type session: int
      :param incoming: Last incoming heartbeat processed from peer.
      :type incoming: int
      :param outgoing: Outgoing heartbeat.
      :type outgoing: int
      :param discard: Optional data that is discared by peer.
      :type discard: str
      """
      Message.__init__(self)
      self.session = session
      self.incoming = incoming
      self.outgoing = outgoing
      self.discard = discard


   @staticmethod
   def parse(wmsg):
      """
      Verifies and parses an unserialized raw message into an actual WAMP message instance.

      :param wmsg: The unserialized raw message.
      :type wmsg: list

      :returns obj -- An instance of this class.
      """
      ## this should already be verified by WampSerializer.unserialize
      ##
      assert(len(wmsg) > 0 and wmsg[0] == Heartbeat.MESSAGE_TYPE)

      if len(wmsg) not in [4, 5]:
         raise ProtocolError("invalid message length {} for HEARTBEAT".format(len(wmsg)))

      session = check_or_raise_id(wmsg[1], "'session' in HEARTBEAT")

      incoming = wmsg[2]

      if type(incoming) not in [int, long]:
         raise ProtocolError("invalid type {} for 'incoming' in HEARTBEAT".format(type(incoming)))

      if incoming < 0: # must be non-negative
         raise ProtocolError("invalid value {} for 'incoming' in HEARTBEAT".format(incoming))

      outgoing = wmsg[3]

      if type(outgoing) not in [int, long]:
         raise ProtocolError("invalid type {} for 'outgoing' in HEARTBEAT".format(type(outgoing)))

      if outgoing <= 0: # must be positive
         raise ProtocolError("invalid value {} for 'outgoing' in HEARTBEAT".format(outgoing))

      discard = None
      if len(wmsg) > 4:
         discard = wmsg[4]
         if type(discard) not in (str, unicode):
            raise ProtocolError("invalid type {} for 'discard' in HEARTBEAT".format(type(discard)))

      obj = Heartbeat(session, incoming, outgoing, discard = discard)

      return obj

   
   def marshal(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.marshal`
      """
      if self.discard:
         return [Heartbeat.MESSAGE_TYPE, self.session, self.incoming, self.outgoing, self.discard]
      else:
         return [Heartbeat.MESSAGE_TYPE, self.session, self.incoming, self.outgoing]


   def __str__(self):
      """
      Implements :func:`autobahn.wamp.interfaces.IMessage.__str__`
      """
      return "WAMP HEARTBEAT Message (session = {}, incoming = {}, outgoing = {}, len(discard) = {})".format(self.session, self.incoming, self.outgoing, len(self.discard) if self.discard else None)

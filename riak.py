"""
Copyright 2010 Rusty Klophaus <rusty@basho.com>
Copyright 2010 Justin Sheehy <justin@basho.com>
Copyright 2009 Jay Baird <jay@mochimedia.com>

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

# Import libraries.
import sys, random, logging, base64, urllib, re
from cStringIO import StringIO
import types

# Use pycurl as first choice, httplib as second choice.
try:
        import pycurl
        HAS_PYCURL = True
except ImportError:
        import httplib
        HAS_PYCURL = False

# Use json as first choice, simplejson as second choice.
try: 
        import json
except ImportError: 
        import simplejson as json


"""
This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.    
"""

MD_CTYPE    = "content-type"
MD_CHARSET  = "charset"
MD_ENCODING = "content-encoding"
MD_VTAG     = "vtag"
MD_LINKS    = "links"
MD_LASTMOD  = "lastmod"
MD_LASTMOD_USECS = "lastmod-usecs"
MD_USERMETA = "usermeta"


"""
The Riak API for Python allows you to connect to a Riak instance,
create, modify, and delete Riak objects, add and remove links from
Riak objects, run Javascript (and Erlang) based Map/Reduce
operations, and run Linkwalking operations.

See the unit_tests.php file for example usage.

@author Rusty Klophaus (@rklophaus) (rusty@basho.com)
@package RiakAPI
"""

class RiakClient:
        """
        The RiakClient object holds information necessary to connect to
        Riak. The Riak API uses HTTP, so there is no persistent
        connection, and the RiakClient object is extremely lightweight.
        """
        def __init__(self, host='127.0.0.1', port=8098, **kwargs):
                # , prefix='riak', mapred_prefix='mapred'
                """
                Construct a new RiakClient object.
                @param string host - Hostname or IP address (default '127.0.0.1')
                @param int port - Port number (default 8098)
                @param string prefix - Interface prefix (default 'riak')
                @param string mapred_prefix - MapReduce prefix (default 'mapred')
                """
                self._transport = RiakHttpTransport(**kwargs)
                self._r = 2
                self._w = 2
                self._dw = 0
                self._rw = 2
                return None

        def get_transport(self):
                """
                Get a transport object
                """
                return self._transport;

        def get_r(self):
                """
                Get the R-value setting for this RiakClient. (default 2)
                @return integer
                """
                return self._r

        def set_r(self, r):
                """
                Set the R-value for this RiakClient. This value will be used
                for any calls to get(...) or get_binary(...) where where 1) no
                R-value is specified in the method call and 2) no R-value has
                been set in the RiakBucket.
                @param integer r - The R value.
                @return self
                """
                self._r = r
                return self

        def get_w(self):
                """
                Get the W-value setting for this RiakClient. (default 2)
                @return integer
                """
                return self._w

        def set_w(self, w):
                """
                Set the W-value for this RiakClient. See set_r(...) for a
                description of how these values are used.
                @param integer w - The W value.
                @return self
                """
                self._w = w
                return self

        def get_dw(self):
                """
                Get the DW-value for this ClientOBject. (default 2)
                @return integer
                """
                return self._dw
        
        def set_dw(self, dw):
                """
                Set the DW-value for this RiakClient. See set_r(...) for a
                description of how these values are used.
                @param integer dw - The DW value.
                @return self
                """
                self._dw = dw
                return self

        def get_rw(self):
                """
                Get the RW-value for this ClientObject. (default 2)
                @return integer
                """
                return self._rw
        
        def set_rw(self, rw):
                """
                Set the RW-value for this RiakClient. See set_r(...) for a
                description of how these values are used.
                @param integer rw - The RW value.
                @return self
                """
                self._rw = rw
                return self
        
        def get_client_id(self):
                """
                Get the client_id for this RiakClient.
                @return string
                """
                return self._transport.get_client_id()
        
        def set_client_id(self, client_id):
                """
                Set the client_id for this RiakClient. Should not be called
                unless you know what you are doing.
                @param string client_id - The new client_id.
                @return self
                """
                self._transport.set_client_id(client_id)
                return self

        def bucket(self, name):
                """
                Get the bucket by the specified name. Since buckets always exist,
                this will always return a RiakBucket.
                @return RiakBucket
                """
                return RiakBucket(self, name)
        
        def is_alive(self):
                """
                Check if the Riak server for this RiakClient is alive.
                @return boolean
                """
                return self._transport.ping()

        def add(self, *args):
                """
                Start assembling a Map/Reduce operation.
                @see RiakMapReduce.add()
                @return RiakMapReduce
                """
                mr = RiakMapReduce(self)
                return apply(mr.add, args)
        
        def link(self, args):
                """
                Start assembling a Map/Reduce operation.
                @see RiakMapReduce.link()
                """
                mr = RiakMapReduce(self)
                return apply(mr.link, args)
        
        def map(self, *args):
                """
                Start assembling a Map/Reduce operation.
                @see RiakMapReduce.map()
                """
                mr = RiakMapReduce(self)
                return apply(mr.map, args)
        
        def reduce(self, *args):
                """
                Start assembling a Map/Reduce operation.
                @see RiakMapReduce.reduce()
                """
                mr = RiakMapReduce(self)
                return apply(mr.reduce, args)
        
class RiakMapReduce:
        """
        The RiakMapReduce object allows you to build up and run a
        map/reduce operation on Riak.
        @package RiakMapReduce
        """

        def __init__(self, client):
                """
                Construct a Map/Reduce object.
                @param RiakClient client - A RiakClient object.
                @return RiakMapReduce
                """
                self._client = client
                self._phases = []
                self._inputs = []
                self._input_mode = None
        
        def add(self, arg1, arg2=None, arg3=None):
                """
                Add inputs to a map/reduce operation. This method takes three
                different forms, depending on the provided inputs. You can
                specify either a RiakObject, a string bucket name, or a bucket,
                key, and additional arg.
                @param mixed arg1 - RiakObject or Bucket
                @param mixed arg2 - Key or blank
                @param mixed arg3 - Arg or blank
                @return RiakMapReduce
                """
                if (arg2 == None) and (arg3 == None):
                        if isinstance(arg1, RiakObject):
                                return self.add_object(arg1)
                        else:
                                return self.add_bucket(arg1)
                else:
                        return self.add_bucket_key_data(arg1, arg2, arg3)
                
        def add_object(self, obj):
                return self.add_bucket_key_data(obj._bucket._name, obj._key, None)
                
        def add_bucket_key_data(self, bucket, key, data) :
                if self._input_mode == 'bucket':
                        raise Exception('Already added a bucket, can\'t add an object.')
                else:
                        self._inputs.append([bucket, key, data])
                        return self

        def add_bucket(self, bucket) :
                self._input_mode = 'bucket'
                self._inputs = bucket
                return self

        def link(self, bucket='_', tag='_', keep=False):
                """
                Add a link phase to the map/reduce operation.
                @param string bucket - Bucket name (default '_', which means all
                buckets)
                @param string tag - Tag (default '_', which means all buckets)
                @param boolean keep - Flag whether to keep results from this
                stage in the map/reduce. (default False, unless this is the last
                step in the phase)
                @return self
                """
                self._phases.append(RiakLinkPhase(bucket, tag, keep))
                return self
        
        def map(self, function, options=[]):
                """
                Add a map phase to the map/reduce operation.
                @param mixed function - Either a named Javascript function (ie:
                'Riak.mapValues'), or an anonymous javascript function (ie:
                'function(...)  ... ' or an array ['erlang_module',
                'function'].
                @param array() options - An optional associative array
                containing 'language', 'keep' flag, and/or 'arg'.
                @return self
                """
                if isinstance(function, list):
                        language = 'erlang'
                else: 
                        language='javascript'

                mr = RiakMapReducePhase('map',
                                        function,
                                        RiakUtils.get_value('language', options, language),
                                        RiakUtils.get_value('keep', options, False),
                                        RiakUtils.get_value('arg', options, None))
                self._phases.append(mr)
                return self

        def reduce(self, function, options=[]):
                """
                Add a reduce phase to the map/reduce operation.
                @param mixed function - Either a named Javascript function (ie.
                'Riak.mapValues'), or an anonymous javascript function(ie:
                'function(...) { ... }' or an array ['erlang_module', 'function'].
                @param array() options - An optional associative array
                containing 'language', 'keep' flag, and/or 'arg'.
                @return self
                """

                if isinstance(function, list):
                        language = 'erlang'
                else: 
                        language='javascript'

                mr = RiakMapReducePhase('reduce',
                                        function,
                                        RiakUtils.get_value('language', options, language),
                                        RiakUtils.get_value('keep', options, False),
                                        RiakUtils.get_value('arg', options, None))
                self._phases.append(mr)
                return self
                        
        def run(self, timeout=None):
                """
                Run the map/reduce operation. Returns an array of results, or an
                array of RiakLink objects if the last phase is a link phase.
                @param integer timeout - Timeout in seconds.
                @return array()
                """
                # Convert all phases to associative arrays. Also,
                # if none of the phases are accumulating, then set the last one to
                # accumulate.
                num_phases = len(self._phases)
                keep_flag = False
                query = []
                for i in range(num_phases):
                        phase = self._phases[i]
                        if (i == (num_phases - 1)) and (not keep_flag):
                                phase._keep = True
                        if phase._keep: keep_flag = True
                        query.append(phase.to_array())

                # Construct the job, optionally set the timeout...
                job = {'inputs':self._inputs, 'query':query}
                if timeout != None:
                        job['timeout'] = timeout

                content = json.dumps(job)

                # Do the request...
                host = self._client._host
                port = self._client._port
                url = "/" + self._client._mapred_prefix
                response = RiakUtils.http_request('POST', host, port, url, {}, content)
                result = json.loads(response[1])
                
                # If the last phase is NOT a link phase, then return the result.
                lastIsLink = isinstance(self._phases[-1], RiakLinkPhase)
                if not lastIsLink:
                        return result

                # Otherwise, if the last phase IS a link phase, then convert the
                # results to RiakLink objects.
                a = []
                for r in result:
                        link = RiakLink(r[0], r[1], r[2])
                        link._client = self._client
                        a.append(link)

                return a

class RiakMapReducePhase:
        """
        The RiakMapReducePhase holds information about a Map phase or
        Reduce phase in a RiakMapReduce operation.
        """

        def __init__(self, type, function, language, keep, arg):
                """
                Construct a RiakMapReducePhase object.
                @param string type - 'map'placeholder149'reduce'
                @param mixed function - string or array():
                @param string language - 'javascript'placeholder149'erlang'
                @param boolean keep - True to return the output of this phase in
                the results.
                @param mixed arg - Additional value to pass into the map or
                reduce function.
                """
                self._type = type
                self._language = language
                self._function = function
                self._keep = keep
                self._arg = arg
                return None

        def to_array(self):
                """
                Convert the RiakMapReducePhase to an associative array. Used
                internally.
                """
                stepdef = {'keep':self._keep,
                           'language':self._language,
                           'arg':self._arg}
                        
                if (self._language == 'javascript') and isinstance(self._function, list):
                        stepdef['bucket'] = self._function[0]
                        stepdef['key'] = self._function[1]
                elif (self._language == 'javascript') and isinstance(self._function, str):
                        if ("{" in self._function):
                                stepdef['source'] = self._function
                        else:
                                stepdef['name'] = self._function

                elif (self._language == 'erlang' and isinstance(self._function, list)):
                        stepdef['module'] = self._function[0]
                        stepdef['function'] = self._function[1]

                return {self._type : stepdef}

class RiakLinkPhase :
        """
        The RiakLinkPhase object holds information about a Link phase in a
        map/reduce operation.
        @package RiakLinkPhase
        """

        def __init__(self, bucket, tag, keep):
                """
                Construct a RiakLinkPhase object.
                @param string bucket - The bucket name.
                @param string tag - The tag.
                @param boolean keep - True to return results of this phase.
                """
                self._bucket = bucket
                self._tag = tag
                self._keep = keep
                return None

        def to_array(self):
                """
                Convert the RiakLinkPhase to an associative array. Used
                internally.
                """
                stepdef = {'bucket':self._bucket,
                           'tag':self._tag,
                           'keep':self._keep}
                return {'link':stepdef}

class RiakLink :
        """
        The RiakLink object represents a link from one Riak object to
        another.
        @package RiakLink
        """

        def __init__(self, bucket, key, tag=None):
                """
                Construct a RiakLink object.
                @param string bucket - The bucket name.
                @param string key - The key.
                @param string tag - The tag.
                """
                self._bucket = bucket
                self._key = key
                self._tag = tag
                self._client = None
                return None

        def get(self, r=None):
                """
                Retrieve the RiakObject to which this link points.
                @param integer r - The R-value to use.
                @return RiakObject
                """
                return self._client.bucket(self._bucket).get(self._key, r)

        def get_binary(self, r=None):
                """
                Retrieve the RiakObject to which this link points, as a binary.
                @param integer r - The R-value to use.
                @return RiakObject
                """
                return self._client.bucket(self._bucket).get_binary(self._key, r)

        def get_bucket(self):
                """
                Get the bucket name of this link.
                @return string
                """
                return self._bucket

        def set_bucket(self, name):
                """
                Set the bucket name of this link.
                @param string name - The bucket name.
                @return self
                """
                self._bucket = bucket
                return self

        def get_key(self):
                """
                Get the key of this link.
                @return string
                """
                return self._key
        
        def set_key(self, key):
                """
                Set the key of this link.
                @param string key - The key.
                @return self
                """
                self._key = key
                return self

        def get_tag(self):
                """
                Get the tag of this link.
                @return string
                """
                if (self._tag == None):
                        return self._bucket
                else:
                        return self._tag

        def set_tag(self, tag):
                """
                Set the tag of this link.
                @param string tag - The tag.
                @return self
                """
                self._tag = tag
                return self

        def to_link_header(self, client):
                """
                Convert this RiakLink object to a link header string. Used internally.
                """
                link = ''
                link += '</'
                link += client._prefix + '/'
                link += urllib.quote_plus(self._bucket) + '/'
                link += urllib.quote_plus(self._key) + '>; riaktag="'
                link += urllib.quote_plus(self.get_tag()) + '"'
                return link

        def isEqual(self, link):
                """
                Return True if the links are equal.
                @param RiakLink link - A RiakLink object.
                @return boolean
                """
                is_equal = (self._bucket == link._bucket) and (self._key == link._key) and (self.get_tag() == link.get_tag())
                return is_equal

class RiakBucket :
        """
        The RiakBucket object allows you to access and change information
        about a Riak bucket, and provides methods to create or retrieve
        objects within the bucket.
        @package RiakBucket
        """

        def __init__(self, client, name):
                self._client = client
                self._name = name
                self._r = None
                self._w = None
                self._dw = None
                self._rw = None
                self._props = None
                return None

        def get_name(self):
                """
                Get the bucket name.
                """
                return self._name

        def get_r(self, r=None):
                """
                Get the R-value for this bucket, if it is set, otherwise return
                the R-value for the client.
                @return integer
                """
                if (r != None):
                        return r
                if (self._r != None):
                        return self._r
                return self._client.get_r()

        def set_r(self, r):
                """
                Set the R-value for this bucket. get(...) and get_binary(...)
                operations that do not specify an R-value will use this value.
                @param integer r - The new R-value.
                @return self
                """
                self._r = r
                return self
                                                         
        def get_w(self, w):
                """
                Get the W-value for this bucket, if it is set, otherwise return
                the W-value for the client.
                @return integer
                """
                if (w != None):
                        return w
                if (self._w != None):
                        return self._w
                return self._client.get_w()
        
        def set_w(self, w):
                """
                Set the W-value for this bucket. See set_r(...) for more information.
                @param integer w - The new W-value.
                @return self
                """
                self._w = w
                return self

        def get_dw(self, dw):
                """
                Get the DW-value for this bucket, if it is set, otherwise return
                the DW-value for the client.
                @return integer
                """
                if (dw != None):
                        return dw
                if (self._dw != None):
                        return self._dw
                return self._client.get_dw()
                                                         
        def set_dw(self, dw):
                """
                Set the DW-value for this bucket. See set_r(...) for more information.
                @param integer dw - The new DW-value
                @return self
                """
                self._dw = dw
                return self
                                                         
        def get_rw(self, rw):
                """
                Get the RW-value for this bucket, if it is set, otherwise return
                the RW-value for the client.
                @return integer
                """
                if (rw != None):
                        return rw
                if (self._rw != None):
                        return self._rw
                return self._client.get_rw()
                                                         
        def set_rw(self, rw):
                """
                Set the RW-value for this bucket. See set_r(...) for more information.
                @param integer rw - The new RW-value
                @return self
                """
                self._rw = rw
                return self
                                                         
        def new(self, key, data=None):
                """
                Create a new Riak object that will be stored as JSON.
                @param string key - Name of the key.
                @param object data - The data to store. (default None)
                @return RiakObject
                """
                obj = RiakObject(self._client, self, key)
                obj.set_data(data)
                obj.set_content_type('text/json')
                obj._jsonize = True
                return obj
        
        def new_binary(self, key, data, content_type='text/json'):
                """
                Create a new Riak object that will be stored as plain text/binary.
                @param string key - Name of the key.
                @param object data - The data to store.
                @param string content_type - The content type of the object. (default 'text/json')
                @return RiakObject
                """
                obj = RiakObject(self._client, self, key)
                obj.set_data(data)
                obj.set_content_type('text/json')
                obj._jsonize = False
                return obj

        def get(self, key, r=None):
                """
                Retrieve a JSON-encoded object from Riak.
                @param string key - Name of the key.
                @param int r - R-Value of the request (defaults to bucket's R)
                @return RiakObject
                """
                obj = RiakObject(self._client, self, key)
                obj._jsonize = True
                r = self.get_r(r)
                return obj.reload(r)

        def get_binary(self, key, r=None):
                """
                Retrieve a binary/string object from Riak.
                @param string key - Name of the key.
                @param int r - R-Value of the request (defaults to bucket's R)
                @return RiakObject
                """
                obj = RiakObject(self._client, self, key)
                obj._jsonize = False
                r = self.get_r(r)
                return obj.reload(r)

        def set_n_val(self, nval):
                """
                Set the N-value for this bucket, which is the number of replicas
                that will be written of each object in the bucket. Set this once
                before you write any data to the bucket, and never change it
                again, otherwise unpredictable things could happen. This should
                only be used if you know what you are doing.
                @param integer nval - The new N-Val.
                """
                return self.set_property('n_val', nval)

        def get_n_val(self):
                """
                Retrieve the N-value for this bucket.
                @return integer                                                         
                """
                return self.get_property('n_val')

        def set_allow_multiples(self, bool):
                """
                If set to True, then writes with conflicting data will be stored
                and returned to the client. This situation can be detected by
                calling has_siblings() and get_siblings(). This should only be used
                if you know what you are doing.
                @param boolean bool - True to store and return conflicting writes.                                                         
                """
                return self.set_property('allow_mult', bool)

        def get_allow_multiples(self):
                """
                Retrieve the 'allow multiples' setting.
                @return Boolean
                """
                return self.get_property('allow_mult') == True

        def set_property(self, key, value):
                """
                Set a bucket property. This should only be used if you know what
                you are doing.
                @param string key - Property to set.
                @param mixed value - Property value.                                                         
                """
                return self.set_properties({key : value})

        def get_property(self, key):
                """
                Retrieve a bucket property.
                @param string key - The property to retrieve.
                @return mixed
                """
                props = self.get_properties()
                if (key in props.keys()):
                        return props[key]
                else:
                        return None

        def set_properties(self, props):
                """
                Set multiple bucket properties in one call. This should only be
                used if you know what you are doing.
                @param array props - An associative array of key:value.        
                """
                t = self._client.get_transport()
                t.set_bucket_props(self, props)
                return None

        def get_properties(self):
                """
                Retrieve an associative array of all bucket properties.
                @return Array		
                """
                t = self._client.get_transport()
                return t.get_bucket_props(self)
               

class RiakObject :
        """
        The RiakObject holds meta information about a Riak object, plus the
        object's data.
        @package RiakObject	
        """

        def __init__(self, client, bucket, key=None):
                """
                Construct a new RiakObject.
                @param RiakClient client - A RiakClient object.
                @param RiakBucket bucket - A RiakBucket object.
                @param string key - An optional key. If not specified, then key
                is generated by server when store(...) is called.		
                """
                self._client = client
                self._bucket = bucket
                self._key = key
                self._jsonize = True
                self._vclock = None
                self._data = None
                self._metadata = {}
                self._links = []
                self._siblings = []
                self._exists = False
                return None

        def get_bucket(self):
                """
                Get the bucket of this object.
                @return RiakBucket
                """
                return self._bucket;

        def get_key(self):
                """
                Get the key of this object.
                @return string
                """
                return self._key


        def get_data(self):
                """
                Get the data stored in this object. Will return a associative
                array, unless the object was constructed with new_binary(...) or
                get_binary(...), in which case this will return a string.
                @return array or string		
                """
                return self._data
        
        def set_data(self, data):
                """
                Set the data stored in this object. This data will be
                JSON encoded unless the object was constructed with
                new_binary(...) or get_binary(...).
                @param mixed data - The data to store.
                @return data		
                """
                self._data = data
                return self
  
        def get_encoded_data(self):
                """
                Get the data encoded for storing	
                """
                if self._jsonize == True:
                        return json.dumps(self._data)
                else:
                        return self._data
 
        def set_encoded_data(self, data):
                """
                Get the data encoded for storing	
                """
                if self._jsonize == True:
                        self._data = json.loads(data)
                else:
                        self._data = data
                return self
      
         
        def get_metadata(self):
                """
                Get the metadata stored in this object. Will return a associative
                array
                @return dict
                """
                return self._data
        
        def set_metadata(self, metadata):
                """
                Set the metadata stored in this object. 
                @param dict metadata - The data to store.
                @return data		
                """
                self._metadata = metadata
                return self
        
        def exists(self):
                """
                Return True if the object exists, False otherwise. Allows you to
                detect a get(...) or get_binary(...) operation where the object is missing.
                @return boolean
                """
                return self._exists
        
        def get_content_type(self):
                """
                Get the content type of this object. This is either text/json, or
                the provided content type if the object was created via new_binary(...).
                @return string
                """
                return self._metadata[MD_CTYPE]
        
        def set_content_type(self, content_type):
                """
                Set the content type of this object.
                @param string content_type - The new content type.
                @return self		
                """
                self._metadata[MD_CTYPE] = content_type
                return self
        
        def add_link(self, obj, tag=None):
                """
                Add a link to a RiakObject.
                @param mixed obj - Either a RiakObject or a RiakLink object.
                @param string tag - Optional link tag. (default is bucket name,
                ignored if obj is a RiakLink object.)
                @return RiakObject		
                """
                if isinstance(obj, RiakLink):
                        newlink = obj
                else:
                        newlink = RiakLink(obj._bucket._name, obj._key, tag)
                        
                self.remove_link(newlink)
                self._links.append(newlink)
                return self
                
        def remove_link(self, obj, tag=None):
                """
                Remove a link to a RiakObject.
                @param mixed obj - Either a RiakObject or a RiakLink object.
                @param string tag -
                @param mixed obj - Either a RiakObject or a RiakLink object.
                @param string tag - Optional link tag. (default is bucket name,
                ignored if obj is a RiakLink object.)
                @return self		
                """
                if isinstance(obj, RiakLink):
                        oldlink = obj
                else:
                        oldlink = RiakLink(obj._bucket._name, obj._key, tag)
                        
                a = []
                for link in self._links:
                        if not link.isEqual(oldlink):
                                a.append(link)

                self._links = a
                return self

        def get_links(self):
                """
                Return an array of RiakLink objects.
                @return array()		
                """
                # Set the clients before returning...
                for link in self._links:
                        link._client = self._client
                return self._links
                        
        def store(self, w=None, dw=None):
                """
                Store the object in Riak. When this operation completes, the
                object could contain new metadata and possibly new data if Riak
                contains a newer version of the object according to the object's
                vector clock.
                @param integer w - W-value, wait for this many partitions to respond
                before returning to client.
                @param integer dw - DW-value, wait for this many partitions to
                confirm the write before returning to client.
                @return self		
                """
                # Use defaults if not specified...
                w = self._bucket.get_w(w)
                dw = self._bucket.get_dw(w)
                
                # Issue the get over our transport
                t = self._client.get_transport()
                Result = t.put(self, w, dw)
                if Result != None:
                        self.populate(Result)

                return self


        def reload(self, r=None, vtag=None):
                """
                Reload the object from Riak. When this operation completes, the
                object could contain new metadata and a new value, if the object
                was updated in Riak since it was last retrieved.
                @param integer r - R-Value, wait for this many partitions to respond
                before returning to client.
                @return self		
                """
                # Do the request...
                r = self._bucket.get_r(r)
                t = self._client.get_transport()
                Result = t.get(self, r, vtag)

                self.clear()
                if Result != None:
                        self.populate(Result)

                return self


        def delete(self, rw=None):
                """
                Delete this object from Riak.
                @param integer rw - RW-value. Wait until this many partitions have
                deleted the object before responding.
                @return self		
                """
                # Use defaults if not specified...
                rw = self._bucket.get_rw(rw)
                t = self._client.get_transport()
                Result = t.delete(self, rw)
                self.clear()
                return self
                        
        def clear(self) :
                """
                Reset this object.
                @return self		
                """
                self._headers = []
                self._links = []
                self._data = None
                self._exists = False
                self._siblings = []
                return self
        
        def vclock(self) :
                """
                Get the vclock of this object.
                @return string		
                """
                return self._vclock

        def populate(self, Result) :
                """
                Populate the object based on the return from get.
                If None returned, then object is not found
                If a tuple of vclock, contents then one or more
                whole revisions of the key were found
                If a list of vtags is returned there are multiple
                sibling that need to be retrieved with get.
                """
                self.clear()                
                if Result == None:
                        return self
                elif type(Result) == types.ListType:
                        self.set_siblings(Result)
                elif type(Result) == types.TupleType:
                        (vclock, contents) = Result
                        (metadata, data) = contents.pop(0)
                        self._vclock = vclock
                        self._exists = True
                        self.set_metadata(metadata)
                        self.set_encoded_data(data)
                        # Create objects for all siblings
                        siblings = [self]
                        for (metadata, data) in contents:
                                sibling = copy.copy(self)
                                sibling.set_metadata(metadata)
                                sibling.set_data(data)
                        for sibling in siblings:
                                sibling.set_siblings(siblings)

        def populate_links(self, linkHeaders) :
                """
                Private.
                @return self		
                """
                for linkHeader in linkHeaders.strip().split(','):
                        linkHeader = linkHeader.strip()
                        matches = re.match("\<\/([^\/]+)\/([^\/]+)\/([^\/]+)\>; ?riaktag=\"([^\']+)\"", linkHeader)
                        if (matches != None):
                                link = RiakLink(matches.group(2), matches.group(3), matches.group(4))
                                self._links.append(link)
                return self

        def has_siblings(self):
                """
                Return True if this object has siblings.
                @return boolean
                """
                return(self.get_sibling_count() > 0)
        
        def get_sibling_count(self):
                """
                Get the number of siblings that this object contains.
                @return integer		
                """
                return len(self._siblings)
        
        def get_sibling(self, i, r=None):
                """
                Retrieve a sibling by sibling number.
                @param  integer i - Sibling number.
                @param  integer r - R-Value. Wait until this many partitions
                have responded before returning to client.
                @return RiakObject.		
                """
                if isinstance(self._siblings[i], RiakObject):
                        return self._siblings[i]
                else:
                        # Use defaults if not specified.
                        r = self._bucket.get_r(r)
                
                        # Run the request...
                        vtag = self._siblings[i]
                        obj = RiakObject(self._client, self._bucket, self._key)
                        obj.reload(r, vtag)
                        self._siblings[i] = obj
                        return obj

        def get_siblings(self, r=None):
                """
                Retrieve an array of siblings.
                @param integer r - R-Value. Wait until this many partitions have
                responded before returning to client.
                @return array of RiakObject		
                """
                a = [self]
                for i in range(self.get_sibling_count()):
                        a.append(self.get_sibling(i, r))
                return a
                
        def set_siblings(self, siblings):
                """
                Set the array of siblings - used internally
                Make sure this object is at index 0 so get_siblings(0) always returns
                the current object
                """
                try:
                        i = siblings.index(self)
                        if i != 0:
                                siblings.pop(i)
                                siblings.insert(0, self)
                except ValueError:
                        pass

                if len(siblings) > 1:
                        self._siblings = siblings
                else:
                        self._siblings = []

        def add(self, *args):
                """
                Start assembling a Map/Reduce operation.
                @see RiakMapReduce.add()
                @return RiakMapReduce		
                """
                mr = RiakMapReduce(self._client)
                mr.add(self._bucket._name, self._key)
                return apply(mr.add, args)
        
        def link(self, *args):
                """
                Start assembling a Map/Reduce operation.
                @see RiakMapReduce.link()
                @return RiakMapReduce		
                """
                mr = RiakMapReduce(self._client)
                mr.add(self._bucket._name, self._key)
                return apply(mr.link, args)
        
        def map(self, *args):
                """
                Start assembling a Map/Reduce operation.
                @see RiakMapReduce.map()
                @return RiakMapReduce
                """
                mr = RiakMapReduce(self._client)
                mr.add(self._bucket._name, self._key)
                return apply(mr.map, args)
        
        def reduce(self, params):
                """
                Start assembling a Map/Reduce operation.
                @see RiakMapReduce.reduce()
                @return RiakMapReduce
                """
                mr = RiakMapReduce(self._client)
                mr.add(self._bucket._name, self._key)
                return apply(mr.reduce, args)
        
class RiakUtils :
        """
        Utility functions used by Riak library.
        @package RiakUtils	
        """
        @classmethod
        def get_value(self, key, array, defaultValue) :
                if (key in array):
                        return array[key]
                else:
                        return defaultValue
		
                       

class RiakError(Exception) :
        def __init__(self, value):
                self.value = value
        def __str__(self):
                return repr(self.value)
 
class RiakTransport :
        """
        Class to encapsulate transport details
        """
        
        def ping(self):
                """
                Ping the remote server
                @return boolean
                """
                raise RiakError("not implemented")
        
        def get(self, robj, r = None, vtag = None):
                """
                Serialize get request and deserialize response
                @return (vclock=None, [(metadata, value)]=None)
                """
                raise RiakError("not implemented")
        
        def put(self, robj, w = None, dw = None):
                """
                Serialize put request and deserialize response - if 'content'
                is true, retrieve the updated metadata/content
                @return (vclock=None, [(metadata, value)]=None)
                """
                raise RiakError("not implemented")
        
        def delete(self, robj, rw = None):
                """
                Serialize delete request and deserialize response
                @return true
                """
                raise RiakError("not implemented")
        
        def get_bucket_props(self, bucket) :
                """
                Serialize get bucket property request and deserialize response
                @return dict()
                """
                raise RiakError("not implemented")
        
        def set_bucket_props(self, bucket, props) :
                """
                Serialize set bucket property request and deserialize response
                bucket = bucket object
                props = dictionary of properties
                @return boolean
                """
                raise RiakError("not implemented")
        
        def mapred(self, inputs, query) :
                """
                Serialize map/reduce request
                """
                raise RiakError("not implemented")
        
class RiakHttpTransport(RiakTransport) :
        """
        The RiakHttpTransport object holds information necessary to connect to
        Riak. The Riak API uses HTTP, so there is no persistent
        connection, and the RiakClient object is extremely lightweight.
        """
        def __init__(self, host='127.0.0.1', port=8098, prefix='riak', mapred_prefix='mapred'):
                """
                Construct a new RiakClient object.
                @param string host - Hostname or IP address (default '127.0.0.1')
                @param int port - Port number (default 8098)
                @param string prefix - Interface prefix (default 'riak')
                @param string mapred_prefix - MapReduce prefix (default 'mapred')
                """
                self._host = host
                self._port = port
                self._prefix = prefix
                self._mapred_prefix = mapred_prefix
                self._client_id = 'php_' + base64.b64encode(str(random.randint(1, 1073741824)))
                return None

        """
        Check server is alive over HTTP
        """
        def ping(self) :
                response = self.http_request('GET', self._host, self._port, '/ping')
                return(response != None) and (response[1] == 'OK')

        """
        Get a bucket/key from the server
        """
        def get(self, robj, r, vtag = None) :
                params = {'r' : r}
                if vtag != None:
                        params['vtag'] = vtag
                host, port, url = self.build_rest_path(robj.get_bucket(), robj.get_key(),
                                                       None, params)
                response = self.http_request('GET', host, port, url)
                return self.parse_body(response, [200, 300, 404])

        def put(self, robj, w = None, dw = None):
                """
                Serialize put request and deserialize response
                """
               # Construct the URL...
                params = {'returnbody' : 'true', 'w' : w, 'dw' : dw}
                host, port, url = self.build_rest_path(robj.get_bucket(), robj.get_key(),
                                                       None, params)
                
                # Construct the headers...
                headers = {'Accept' : 'text/plain, */*; q=0.5',
                           'Content-Type' : robj.get_content_type(),
                           'X-Riak-ClientId' : self._client_id}
                
                # Add the vclock if it exists...
                if (robj.vclock() != None):
                        headers['X-Riak-Vclock'] = robj.vclock()
                        
                # Create the header from metadata
                links = robj.get_links()
                if links != []:
                        headers['Link'] = ''
                        for link in links:
                                if headers['Link'] != '': headers['Link'] += ', '
                                headers['Link'] += self.to_link_header(link)

                content = robj.get_encoded_data()

                # Run the operation.
                response = self.http_request('PUT', host, port, url, headers, content)
                return self.parse_body(response, [200, 300])

        def delete(self, robj, rw):
                # Construct the URL...
                params = {'rw' : rw}
                host, port, url = self.build_rest_path(robj.get_bucket(), robj.get_key(),
                                                       None, params)
                # Run the operation..
                response = self.http_request('DELETE', host, port, url)
                self.check_http_code(response, [204, 404])
                return self


        def get_bucket_props(self, bucket):
                # Run the request...
                params = {'props' : 'True', 'keys' : 'False'}
                host, port, url = self.build_rest_path(bucket, None, None, params)
                response = self.http_request('GET', host, port, url)
                
                headers = response[0]
                encoded_props = response[1]
                if (headers['http_code'] == 200):
                        props = json.loads(encoded_props)
                        return props['props']
                else:
                        raise Exception('Error getting bucket properties.')


        def set_bucket_props(self, bucket, props):
                """
                Set the properties on the bucket object given
                """
                host, port, url = self.build_rest_path(bucket)
                headers = {'Content-Type' : 'application/json'}
                content = json.dumps({'props' : props})
	
                #Run the request...
                response = self.http_request('PUT', host, port, url, headers, content)

                # Handle the response...
                if (response == None):
                        raise Exception('Error setting bucket properties.')
        
                # Check the response value...
                status = response[0]['http_code']
                if (status != 204):
                        raise Exception('Error setting bucket properties.')

    
        def check_http_code(self, response, expected_statuses):
                status = response[0]['http_code']
                if (not status in expected_statuses):
                        m = 'Expected status ' + str(expected_statuses) + ', received ' + str(status)
                        raise Exception(m)
                
        def parse_body(self, response, expected_statuses):
                """
                Given the output of RiakUtils.http_request and a list of
                statuses, populate the object. Only for use by the Riak client
                library.
                @return self		
                """
                # If no response given, then return.
                if (response == None):
                        return self

                # Make sure expected code came back
                self.check_http_code(response, expected_statuses)

                # Update the object...
                headers = response[0]
                data = response[1]
                status = headers['http_code']
          
                # Check if the server is down(status==0)
                if (status == 0):
                        m = 'Could not contact Riak Server: http://' + self._client._host + ':' + str(self._client._port) + '!'
                        raise RiakError(m)

                # Verify that we got one of the expected statuses. Otherwise, raise an exception.
                if (not status in expected_statuses):
                        m = 'Expected status ' + str(expected_statuses) + ', received ' + str(status)
                        raise RiakError(m)

                # If 404(Not Found), then clear the object.
                if (status == 404):
                        return None

                # If 300(Siblings), then return the list of siblings
                elif (status == 300):
                        # Parse and get rid of 'Siblings:' string in element 0
                        siblings = data.strip().split('\n')
                        siblings.pop(0)
                        return siblings
                      
                # Parse the headers...
                vclock = None
                metadata = {}
                links = []
                for header, value in headers.iteritems():
                        if header == 'content-type':
                                metadata[MD_CTYPE] = value
                        elif header == 'charset':
                                metadata[MD_CHARSET] = value
                        elif header == 'content-encoding':
                                metadata[MD_CTYPE] = value
                        elif header == 'etag':
                                metadata[MD_VTAG] = value
                        elif header =='link':
                                self.parse_links(links, headers['link'])
                        elif header == 'last-modified':
                                metadata[MD_LASTMOD] = value
                        elif header.startswith('x-riak-meta-'):
                                metadata[MD_USERMETA][header] = value
                        elif header == 'x-riak-vclock':
                                vclock = value
                if links != []:
                        metadata[MD_LINKS] = links

                return (vclock, [(metadata, data)])

        def to_link_header(self, link):
                """
                Convert this RiakLink object to a link header string. Used internally.
                """
                header = ''
                header += '</'
                header += client._prefix + '/'
                header += urllib.quote_plus(link.get_bucket()) + '/'
                header += urllib.quote_plus(link.get_key()) + '>; riaktag="'
                header += urllib.quote_plus(link.get_tag()) + '"'
                return link

        def parse_links(self, links, linkHeaders) :
                """
                Private.
                @return self		
                """
                for linkHeader in linkHeaders.strip().split(','):
                        linkHeader = linkHeader.strip()
                        matches = re.match("\<\/([^\/]+)\/([^\/]+)\/([^\/]+)\>; ?riaktag=\"([^\']+)\"", linkHeader)
                        if (matches != None):
                                link = RiakLink(matches.group(2), matches.group(3), matches.group(4))
                                links.append(link)
                return self


        """
        Utility functions used by Riak library.
        @package RiakUtils	
        """
        @classmethod
        def get_value(self, key, array, defaultValue) :
                if (key in array):
                        return array[key]
                else:
                        return defaultValue
		
        def build_rest_path(self, bucket, key=None, spec=None, params=None) :
                """
                Given a RiakClient, RiakBucket, Key, LinkSpec, and Params,
                construct and return a URL.		
                """
                # Build 'http://hostname:port/prefix/bucket'
                path = ''
		path += '/' + self._prefix
		path += '/' + urllib.quote_plus(bucket._name)

                # Add '.../key'
                if (key != None):
                        path += '/' + urllib.quote_plus(key)
                        
                # Add query parameters.
                if (params != None):
                        s = ''
                        for key in params.keys():
                                if (s != ''): s += '&'
                                s += urllib.quote_plus(key) + '=' + urllib.quote_plus(str(params[key]))
                        path += '?' + s

                # Return.
                return self._host, self._port, path

        @classmethod
        def http_request(self, method, host, port, url, headers = {}, obj = '') :
                """
                Given a Method, URL, Headers, and Body, perform and HTTP request,
                and return an array of arity 2 containing an associative array of
                response headers and the response body.
                """
                if HAS_PYCURL:
                        return self.pycurl_request(method, host, port, url, headers, obj)
                else:
                        return self.httplib_request(method, host, port, url, headers, obj)


        @classmethod
        def httplib_request(self, method, host, port, uri, headers={}, body=''):
                # Run the request...
                client = None
                response = None
                try:
                        client = httplib.HTTPConnection(host, port)
                        client.request(method, uri, body, headers)
                        response = client.getresponse()

                        # Get the response headers...
                        response_headers = {}
                        response_headers['http_code'] = response.status
                        for (key, value) in response.getheaders():
                                response_headers[key.lower()] = value

                        # Get the body...
                        response_body = response.read()
                        response.close()

                        return response_headers, response_body
                except:
                        if client != None: client.close()
                        if response != None: response.close()
                        raise

        
        @classmethod
        def pycurl_request(self, method, host, port, uri, headers={}, body=''):
                url = "http://" + host + ":" + str(port) + uri
                # Set up Curl...
                client = pycurl.Curl()
                client.setopt(pycurl.URL, url)                
                client.setopt(pycurl.HTTPHEADER, self.build_headers(headers))
                if method == 'GET':
                        client.setopt(pycurl.HTTPGET, 1)
                elif method == 'POST':
                        client.setopt(pycurl.POST, 1)                        
                        client.setopt(pycurl.POSTFIELDS, body)
                elif method == 'PUT':
                        client.setopt(pycurl.CUSTOMREQUEST, method)        
                        client.setopt(pycurl.POSTFIELDS, body)
                elif method == 'DELETE':
                        client.setopt(pycurl.CUSTOMREQUEST, method)

                # Capture the response headers...
                response_headers_io = StringIO()
                client.setopt(pycurl.HEADERFUNCTION, response_headers_io.write)
                
                # Capture the response body...
                response_body_io = StringIO()
                client.setopt(pycurl.WRITEFUNCTION, response_body_io.write)

                try:
                        # Run the request.
                        client.perform()
                        http_code = client.getinfo(pycurl.HTTP_CODE)
                        client.close()
                        
                        # Get the headers...
                        response_headers = self.parse_http_headers(response_headers_io.getvalue())
                        response_headers['http_code'] = http_code
                        
                        # Get the body...
                        response_body = response_body_io.getvalue()

                        return response_headers, response_body
                except:
                        if (client != None) : client.close()
                        raise

        @classmethod
        def build_headers(self, headers):
                headers1 = []
                for key in headers.keys():
                        headers1.append('%s: %s' % (key, headers[key]))
                return headers1

        @classmethod
        def parse_http_headers(self, headers) :
                """
                Parse an HTTP Header string into an asssociative array of
                response headers.		
                """
                retVal = {}
                fields = headers.split("\n")
                for field in fields:
                        matches = re.match("([^:]+):(.+)", field)
                        if (matches == None): continue
                        key = matches.group(1).lower()
                        value = matches.group(2).strip()
                        if (key in retVal.keys()):
                                if  isinstance(retVal[key], list):
                                        retVal[key].append(value)
                                else:
                                        retVal[key] = [retVal[key]].append(value)
                        else:
                                retVal[key] = value
                return retVal
        
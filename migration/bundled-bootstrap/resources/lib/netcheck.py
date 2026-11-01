"""Google Drive network diagnostics: which TLS path reaches each host from this device. No response bodies or account data."""
import http.client,os,socket,ssl,sys
HOSTS=[('Drive sign-in server','drive.signinserver.com','/ip'),('Google Drive API','www.googleapis.com','/discovery/v1/apis/drive/v3/rest'),('TMDb (works in Kodi)','api.themoviedb.org','/3/configuration')]

def contexts(certifi_path):
 yield 'python default',ssl.create_default_context
 if certifi_path:
  yield 'certifi',lambda:ssl.create_default_context(cafile=certifi_path)
  def capped():
   context=ssl.create_default_context(cafile=certifi_path);context.maximum_version=ssl.TLSVersion.TLSv1_2;return context
  yield 'certifi TLS 1.2',capped

def describe(error):
 # Exception class and SSL fields only; messages from these hosts carry no account data.
 info={'error':type(error).__name__,'message':str(error)[:200]}
 for name in ['library','reason','verify_code','verify_message','errno']:
  value=getattr(error,name,None)
  if value is not None:info[name]=value
 return info

def run(certifi_path=None,kodi_fetch=None,timeout=15):
 report={'python':sys.version.split()[0],'openssl':ssl.OPENSSL_VERSION,'ssl_cert_file':os.environ.get('SSL_CERT_FILE'),'certifi':certifi_path,'hosts':{}}
 report['ssl_cert_file_exists']=bool(report['ssl_cert_file']) and os.path.isfile(report['ssl_cert_file'])
 for label,host,path in HOSTS:
  result={}
  try:result['addresses']=sorted({'IPv6' if family==socket.AF_INET6 else 'IPv4' for family,*_ in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)})
  except Exception as error:result['dns']=describe(error)
  for name,factory in contexts(certifi_path):
   connection=None
   try:
    connection=http.client.HTTPSConnection(host,443,timeout=timeout,context=factory());connection.request('GET',path,headers={'User-Agent':'Kodi-iOS diagnostics'})
    response=connection.getresponse();response.read()
    result[name]={'status':response.status,'tls':connection.sock.version() if connection.sock else None}
   except Exception as error:result[name]=describe(error)
   finally:
    if connection:connection.close()
  if kodi_fetch:
   try:result['kodi curl']={'bytes':len(kodi_fetch('https://'+host+path))}
   except Exception as error:result['kodi curl']=describe(error)
  report['hosts'][label]=result
 return report

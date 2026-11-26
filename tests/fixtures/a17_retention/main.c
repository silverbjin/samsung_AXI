#include <pthread.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
static void *worker(void *arg){
 void *h=dlopen((const char*)arg,RTLD_NOW|RTLD_LOCAL);
 if(!h){fprintf(stderr,"%s\n",dlerror());return (void*)2;}
 int (*fn)(void)=dlsym(h,"register_tsd");if(!fn||fn())return (void*)2;
 if(dlclose(h))return (void*)2;
 puts("DLCLOSE_RETURNED");fflush(stdout);return NULL;
}
int main(int argc,char **argv){if(argc!=2)return 2;pthread_t t;void *r;if(pthread_create(&t,NULL,worker,argv[1])||pthread_join(t,&r)||r)return 2;puts("JOINED");return 0;}

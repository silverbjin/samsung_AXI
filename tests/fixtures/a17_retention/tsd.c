#include <pthread.h>
#include <stdio.h>
static void destructor(void *v){(void)v;puts("TSD_DESTRUCTOR_RAN");}
int register_tsd(void){pthread_key_t k; if(pthread_key_create(&k,destructor))return 2;return pthread_setspecific(k,(void*)1);}

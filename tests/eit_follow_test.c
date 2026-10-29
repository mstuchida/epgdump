#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <string.h>
#include <time.h>
#include "../eit.h"
extern SVT_CONTROL *svttop;
extern void dumpXML(FILE *,char *);
static void event(int table,int version,int id,int hour,int duration,int current,int unknown) {
    unsigned char data[4096]={0};
    data[0]=table;data[1]=0xf0;data[2]=27;data[3]=0x04;data[4]=0x30;
    data[5]=0xc0 | (version<<1) | current; data[9]=1;data[11]=1;data[13]=table;
    data[14]=id>>8;data[15]=id;data[16]=0xed;data[17]=0x8a;data[18]=hour;
    data[21]=duration;data[24]=0x80;
    if(unknown) memset(data+16,0xff,5);
    dumpEIT(data,svttop);
}
static EIT_CONTROL *find(int id){for(EIT_CONTROL *p=svttop->next->eit->next;p;p=p->next)if(p->event_id==id)return p;return NULL;}
static void xml_contains(int id,int expected) {
    FILE *out=tmpfile();assert(out);dumpXML(out,"27");rewind(out);
    char text[32768]={0};fread(text,1,sizeof(text)-1,out);fclose(out);
    char needle[100];sprintf(needle,"event_id=\"%d\"",id);assert((strstr(text,needle)!=NULL)==expected);
}
int main(void) {
    setenv("TZ","Asia/Tokyo",1);tzset();svttop=calloc(1,sizeof(SVT_CONTROL));
    event(0x50,1,7,0x21,1,1,0); EIT_CONTROL *p=find(7);assert(p);time_t initial=p->start_time;
    event(0x4e,31,7,0x22,2,1,0);assert(p->start_time==initial+3600 && p->duration==7200);
    event(0x50,2,7,0x21,1,1,0);assert(p->duration==7200 && p->start_time==initial+3600);
    event(0x4e,0,7,0x23,3,1,0);assert(p->start_time==initial+7200 && p->duration==10800);
    event(0x4e,31,7,0x22,2,1,0);assert(p->duration==10800);
    event(0x4e,1,7,0x21,1,0,0);assert(p->duration==10800);
    free(p->title);p->title=strdup("match");xml_contains(7,1);
    event(0x4e,1,7,0x23,3,1,1);assert(p->time_unknown);xml_contains(7,0);
    event(0x50,3,7,0x21,1,1,0);assert(p->time_unknown);
    event(0x4e,2,7,0x22,2,1,0);assert(!p->time_unknown);xml_contains(7,1);
    event(0x4e,2,0,0x22,2,1,0);assert(find(0) && find(0)!=p); // event_id=0も有効。
    event(0x4e,2,8,0x22,2,1,0);assert(find(8)); // 同じ開始時刻での番組差し替え。
    event(0x4e,2,9,0x22,2,1,0);EIT_CONTROL *pf=find(9);free(pf->title);pf->title=strdup("pf-only");
    svttop->next->haveeitschedule=0;xml_contains(9,1);
    puts("PASS EIT: p/f priority, schedule order, version wrap, stale versions, current_next, unknown time, event 0, replacement, p/f-only XML");
}

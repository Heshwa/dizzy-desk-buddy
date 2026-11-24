#pragma once
#include <ctime>

// Proleptic Gregorian calendar to UTC seconds, independent of the local RTC timezone.
inline time_t utc_seconds(const tm &calendar) {
    int year=calendar.tm_year+1900;
    int month=calendar.tm_mon+1;
    year-=month<=2;
    const int era=(year>=0?year:year-399)/400;
    const int y=year-era*400;
    const int day=(153*(month+(month>2?-3:9))+2)/5+calendar.tm_mday-1;
    const int64_t days=era*146097+y*365+y/4-y/100+day-719468;
    return (time_t)(days*86400+calendar.tm_hour*3600+calendar.tm_min*60+calendar.tm_sec);
}

#ifndef	__TS_CONTROL_H__
#define	__TS_CONTROL_H__

#include	"util.h"

typedef	struct	_SVT_CONTROL	SVT_CONTROL;
typedef	struct	_EIT_CONTROL	EIT_CONTROL;
typedef	struct	_EIT_EXTENDED_DESCRIPTION	EIT_EXTENDED_DESCRIPTION;

/** 拡張イベント記述子（EITタグ0x4E）の項目。 */
struct	_EIT_EXTENDED_DESCRIPTION{
	char	*item_description;
	char	*item;
};

struct	_SVT_CONTROL{
	SVT_CONTROL	*next ;
	SVT_CONTROL	*prev ;
	int		original_network_id ;		// オリジナルネットワークID
	int		transport_stream_id ;		// トランスポートストリームID
	int		service_id ;				// サービスID
	char	service_name[MAXSECLEN] ;	// サービス名
	EIT_CONTROL	*eit;					// EIT テーブル
	char	haveeitschedule;			// EITスケジュールがあるか。
};

struct	_EIT_CONTROL{
	EIT_CONTROL	*next ;
	EIT_CONTROL	*prev ;
	int		table_id ;
	int version_number;
	int time_unknown;
	int		service_id ;
	int		event_id ;			// イベントID
	int		content_type ;		// コンテントタイプ
	char	*title ;			// タイトル
	char	*subtitle ;			// サブタイトル
	int	extended_description_count;
	EIT_EXTENDED_DESCRIPTION	*extended_descriptions;
	int	duration;				// 時間
	time_t	start_time;			// 開始時刻
};
#endif

Operator Analysis
美东时间: 2026/5/14 16:41:05 北京时间: 2026/5/15 04:41:05
统计了19个REGULAR Alpha（每天前4个），在你可用的运算符中，共有32种运算符被使用，82种运算符未被使用。
'-'有两种含义分别是substract和revers, 此处统一为substrac

Category	Definition	Count	Scope	Level
Arithmetic	add(x, y, filter = false), x + y	4	COMBO,REGULAR,SELECTION	base
Arithmetic	multiply(x ,y, ... , filter=false), x * y	4	COMBO,REGULAR,SELECTION	base
Arithmetic	sign(x)	0	COMBO,REGULAR,SELECTION	base
Arithmetic	subtract(x, y, filter=false), x - y	10	COMBO,REGULAR,SELECTION	base
Arithmetic	pasteurize(x)	0	COMBO,REGULAR	genius
Arithmetic	log(x)	1	COMBO,REGULAR,SELECTION	base
Arithmetic	purify(x)	1	COMBO,REGULAR,SELECTION	genius
Arithmetic	arc_tan(x)	0	COMBO,REGULAR,SELECTION	genius
Arithmetic	max(x, y, ..)	0	COMBO,REGULAR,SELECTION	base
Arithmetic	abs(x)	0	COMBO,REGULAR,SELECTION	base
Arithmetic	sigmoid(x)	0	COMBO,REGULAR,SELECTION	genius
Arithmetic	divide(x, y), x / y	3	COMBO,REGULAR,SELECTION	base
Arithmetic	min(x, y ..)	0	COMBO,REGULAR,SELECTION	base
Arithmetic	tanh(x)	1	COMBO,REGULAR,SELECTION	genius
Arithmetic	nan_out(x, lower=0, upper=0)	0	COMBO,REGULAR,SELECTION	genius
Arithmetic	signed_power(x, y)	4	COMBO,REGULAR,SELECTION	base
Arithmetic	inverse(x)	0	COMBO,REGULAR,SELECTION	base
Arithmetic	round(x)	0	COMBO,REGULAR,SELECTION	genius
Arithmetic	sqrt(x)	0	COMBO,REGULAR,SELECTION	base
Arithmetic	reverse(x)	0	COMBO,REGULAR,SELECTION	base
Arithmetic	power(x, y)	0	COMBO,REGULAR,SELECTION	base
Arithmetic	densify(x)	0	COMBO,REGULAR	base
Arithmetic	floor(x)	0	COMBO,REGULAR,SELECTION	genius
Logical	or(input1, input2)	0	COMBO,REGULAR,SELECTION	base
Logical	and(input1, input2)	0	COMBO,REGULAR,SELECTION	base
Logical	not(x)	0	COMBO,REGULAR,SELECTION	base
Logical	is_nan(input)	0	COMBO,REGULAR,SELECTION	base
Logical	is_not_nan(input)	0	COMBO,REGULAR,SELECTION	genius
Logical	input1 < input2	1	COMBO,REGULAR,SELECTION	base
Logical	input1 == input2	0	COMBO,REGULAR,SELECTION	base
Logical	input1 > input2	0	COMBO,REGULAR,SELECTION	base
Logical	is_finite(input)	0	COMBO,REGULAR,SELECTION	genius
Logical	if_else(input1, input2, input 3)	1	COMBO,REGULAR,SELECTION	base
Logical	input1!= input2	0	COMBO,REGULAR,SELECTION	base
Logical	input1 <= input2	0	COMBO,REGULAR,SELECTION	base
Logical	input1 >= input2	0	COMBO,REGULAR,SELECTION	base
Time Series	ts_corr(x, y, d)	1	COMBO,REGULAR	base
Time Series	ts_zscore(x, d)	9	COMBO,REGULAR	base
Time Series	ts_returns (x, d, mode = 1)	1	COMBO,REGULAR	genius
Time Series	ts_product(x, d)	0	COMBO,REGULAR	base
Time Series	ts_std_dev(x, d)	0	COMBO,REGULAR	base
Time Series	ts_backfill(x,lookback = d, k=1)	3	COMBO,REGULAR	base
Time Series	days_from_last_change(x)	1	COMBO,REGULAR	base
Time Series	last_diff_value(x, d)	0	COMBO,REGULAR	base
Time Series	ts_scale(x, d, constant = 0)	0	COMBO,REGULAR	base
Time Series	ts_entropy(x,d)	0	COMBO,REGULAR	genius
Time Series	ts_step(1)	1	COMBO,REGULAR	base
Time Series	ts_sum(x, d)	0	COMBO,REGULAR	base
Time Series	ts_co_kurtosis(y, x, d)	0	COMBO,REGULAR	genius
Time Series	ts_decay_exp_window(x, d, factor = f)	0	COMBO,REGULAR	genius
Time Series	ts_av_diff(x, d)	2	COMBO,REGULAR	base
Time Series	ts_kurtosis(x, d)	0	COMBO,REGULAR	genius
Time Series	ts_mean(x, d)	8	COMBO,REGULAR	base
Time Series	ts_min_max_diff(x, d, f = 0.5)	0	COMBO,REGULAR	genius
Time Series	ts_arg_max(x, d)	1	COMBO,REGULAR	base
Time Series	ts_min_max_cps(x, d, f = 2)	0	COMBO,REGULAR	genius
Time Series	ts_rank(x, d, constant = 0)	2	COMBO,REGULAR	base
Time Series	ts_ir(x, d)	0	COMBO,REGULAR	genius
Time Series	ts_delay(x, d)	0	COMBO,REGULAR	base
Time Series	ts_theilsen(x, y, d)	0	COMBO,REGULAR	genius
Time Series	hump_decay(x, p=0)	0	COMBO,REGULAR	genius
Time Series	ts_weighted_decay(x, k=0.5)	0	COMBO,REGULAR	genius
Time Series	ts_quantile(x,d, driver="gaussian" )	0	COMBO,REGULAR	base
Time Series	ts_count_nans(x ,d)	0	COMBO,REGULAR	base
Time Series	ts_covariance(y, x, d)	0	COMBO,REGULAR	base
Time Series	ts_co_skewness(y, x, d)	0	COMBO,REGULAR	genius
Time Series	ts_min_diff(x, d)	0	COMBO,REGULAR	genius
Time Series	ts_decay_linear(x, d, dense = false)	2	COMBO,REGULAR	base
Time Series	ts_moment(x, d, k=0)	0	COMBO,REGULAR	genius
Time Series	ts_arg_min(x, d)	0	COMBO,REGULAR	base
Time Series	ts_regression(y, x, d, lag = 0, rettype = 0)	1	COMBO,REGULAR	base
Time Series	ts_skewness(x, d)	0	COMBO,REGULAR	genius
Time Series	ts_max_diff(x, d)	0	COMBO,REGULAR	genius
Time Series	kth_element(x, d, k, ignore=“NaN”)	0	COMBO,REGULAR	base
Time Series	hump(x, hump = 0.01)	0	COMBO,REGULAR	base
Time Series	ts_delta(x, d)	2	COMBO,REGULAR	base
Time Series	ts_poly_regression(y, x, d, k = 1)	0	COMBO,REGULAR	genius
Time Series	ts_target_tvr_decay(x, lambda_min=0, lambda_max=1, target_tvr=0.1)	1	COMBO,REGULAR	genius
Time Series	ts_target_tvr_delta_limit(x, y, lambda_min=0, lambda_max=1, target_tvr=0.1)	0	COMBO,REGULAR	genius
Time Series	ts_target_tvr_hump(x, lambda_min=0, lambda_max=1, target_tvr=0.1)	0	COMBO,REGULAR	genius
Cross Sectional	winsorize(x, std=4)	3	COMBO,REGULAR	base
Cross Sectional	rank(x, rate=2)	15	COMBO,REGULAR	base
Cross Sectional	regression_proj(y, x)	0	COMBO,REGULAR	genius
Cross Sectional	zscore(x)	0	COMBO,REGULAR	base
Cross Sectional	scale(x, scale=1, longscale=1, shortscale=1)	0	COMBO,REGULAR	base
Cross Sectional	normalize(x, useStd = false, limit = 0.0)	0	COMBO,REGULAR	base
Cross Sectional	rank_gmean_amean_diff(input1, input2, input3,...)	0	COMBO,REGULAR	genius
Cross Sectional	quantile(x, driver = gaussian, sigma = 1.0)	0	COMBO,REGULAR	base
Cross Sectional	vector_proj(x, y)	0	COMBO,REGULAR	genius
Vector	vec_kurtosis(x)	1	COMBO,REGULAR	genius
Vector	vec_min(x)	0	COMBO,REGULAR	genius
Vector	vec_count(x)	0	COMBO,REGULAR	genius
Vector	vec_sum(x)	1	COMBO,REGULAR	base
Vector	vec_skewness(x)	0	COMBO,REGULAR	genius
Vector	vec_max(x)	0	COMBO,REGULAR	genius
Vector	vec_avg(x)	3	COMBO,REGULAR	base
Vector	vec_stddev(x)	0	COMBO,REGULAR	genius
Vector	vec_range(x)	0	COMBO,REGULAR	genius
Transformational	bucket(rank(x), range=“0, 1, 0.1”, skipBoth=False, NaNGroup=False) or bucket(rank(x), buckets = “2,5,6,7,10”, skipBoth=False, NaNGroup=False)	0	COMBO,REGULAR	base
Transformational	tail(x, lower = 0, upper = 0, newval = 0)	0	COMBO,REGULAR	genius
Transformational	trade_when(x, y, z)	0	COMBO,REGULAR	base
Group	group_mean(x, weight, group)	0	COMBO,REGULAR	base
Group	group_rank(x, group)	3	COMBO,REGULAR	base
Group	group_vector_proj(x,y,g)	0	COMBO,REGULAR	genius
Group	group_extra(x, weight, group)	0	COMBO,REGULAR	genius
Group	group_backfill(x, group, d, std = 4.0)	0	COMBO,REGULAR	base
Group	group_scale(x, group)	0	COMBO,REGULAR	base
Group	group_count(x, group)	0	COMBO,REGULAR	genius
Group	group_zscore(x, group)	0	COMBO,REGULAR	base
Group	group_std_dev(x, group)	0	COMBO,REGULAR	genius
Group	group_sum(x, group)	1	COMBO,REGULAR	genius
Group	group_neutralize(x, group)	1	COMBO,REGULAR	base
Group	group_cartesian_product(g1, g2)	0	COMBO,REGULAR	genius
Special	inst_pnl(x)	0	COMBO,REGULAR	genius

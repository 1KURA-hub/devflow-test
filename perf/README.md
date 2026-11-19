# DevFlow 性能测试

用 JMeter 对热点流、登录、点赞三个接口做阶梯压测，验证缓存收益、CPU 瓶颈与写热点竞争，并据此定位并修复了一个数据库连接池缺陷。

> ⚠️ **环境说明**：JMeter、Go 服务、MySQL、Redis 全部跑在同一台 Mac（10 核）上，彼此竞争 CPU。
> 因此这里的数值**只能用于横向对比**（修复前后、缓存命中/未命中），**不能当作生产容量结论**。

## 目录

- `gen_jmx.py` 按「场景 / 并发数 / 时长」生成 JMeter 测试计划（`hot` / `login` / `like`）
- `stats.py` 解析 `.jtl`，输出 QPS、P50/P95/P99、错误率
- `run.sh` 一次跑完：生成计划 → 非 GUI 执行 → 输出统计

## 快速开始

```bash
export JAVA_HOME=/path/to/jdk
export PATH="$JAVA_HOME/bin:$JMETER_HOME/bin:$PATH"

# 被测服务需要先起在 :8090（依赖 MySQL / Redis / RabbitMQ）
./perf/run.sh hot   10 20 t10     # 场景 并发数 时长秒 标签
./perf/run.sh login 50 20 t50
./perf/run.sh like  100 20 t100
```

## 测试数据

- 100 个用户、1000 条帖子、2000 条点赞（脚本化造数）
- 点赞场景使用 20 个独立账号轮流压同一篇帖子，制造行锁竞争

## 场景设计

| 场景 | 接口 | 关注点 |
| --- | --- | --- |
| 热点流 | `GET /api/feed/hot` | Redis ZSet 命中 vs 回源 MySQL |
| 登录 | `POST /api/auth/login` | bcrypt 哈希的 CPU 开销 |
| 点赞 | `POST /api/posts/:id/like` | 事务 + 唯一索引的行锁竞争 |

## 结果（连接池修复后，错误率均为 0）

| 场景 | 并发 | QPS | P95 | P99 |
| --- | ---: | ---: | ---: | ---: |
| 热点流（缓存命中） | 10 | 2093 | 6ms | 8ms |
| 热点流（缓存命中） | 50 | 3888 | 18ms | 24ms |
| 热点流（缓存命中） | 100 | 4163 | 35ms | 46ms |
| 热点流（缓存清空） | 10 | 1758 | 7ms | 9ms |
| 点赞 | 10 | 1296 | 9ms | 12ms |
| 点赞 | 50 | 2049 | 40ms | 52ms |
| 点赞 | 100 | 2057 | 76ms | 98ms |
| 登录 | 10 | 133 | 81ms | 100ms |
| 登录 | 50 | 146 | 443ms | 506ms |
| 登录 | 100 | 148 | 1061ms | 1322ms |

## 三个结论

**1. 数据库连接池缺陷（已定位并验证修复）**

修复前 50 并发热点流错误率 89.7%、成功 QPS 仅 65，日志为 `repository/post.go:109 driver: bad connection`。
`internal/db/mysql.go` 未设置任何连接池参数（Go 默认 `MaxOpenConns` 无上限、`MaxIdleConns=2`），高并发下连接频繁建立/复用在已关闭的连接上。

补上 `MaxOpenConns=50`、`MaxIdleConns=25`、`ConnMaxLifetime/IdleTime` 后：

| 50 并发热点流 | 修复前 | 修复后 |
| --- | ---: | ---: |
| 错误率 | 89.7% | 0% |
| 成功 QPS | 65 | 3888 |
| P99 | 123ms | 24ms |

`FLUSH STATUS` 后复压，`Max_used_connections` 稳定在 **51**（池上限 50 + 1 管理连接），确认配置生效。

> 注意：修复前的原始 QPS（如 629）**没有参考价值**——报错请求返回很快，会把吞吐量撑高，必须按成功请求统计。

**2. 登录接口是 CPU 瓶颈**

并发从 10 加到 100，QPS 稳定在 133 → 148，几乎不增长，而 P99 从 100ms 涨到 1322ms，错误率始终为 0。
这是典型的「处理能力饱和、请求排队」：`bcrypt.GenerateFromPassword(..., DefaultCost=10)` 单次约 75ms 纯 CPU 计算，与并发无关。

**3. 点赞是写热点，50 并发后吞吐封顶**

并发 50 → 100，QPS 2049 → 2057（不再增长），P99 52ms → 98ms（翻倍）。
同一篇帖子的 `UPDATE like_count` 争抢同一行锁，增加并发只会增加排队。

## 缓存对比

| 10 并发 | QPS | P99 |
| --- | ---: | ---: |
| 缓存命中 | 2093 | 8ms |
| 缓存清空（`DEL devflow:hot_posts`） | 1758 | 9ms |

缓存带来约 **19%** 的吞吐提升。差距不大，原因是热门榜回源查询本身有索引、且测试数据集较小（1000 帖）。

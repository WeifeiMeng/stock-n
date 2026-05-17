#!/bin/bash
#
# N规则筛选脚本 - 本地执行优化版
#
# 使用说明:
#   ./run_n_rule.sh                  # 执行当天日期的N规则
#   ./run_n_rule.sh 2026-05-13       # 执行指定日期的N规则
#   ./run_n_rule.sh --help           # 显示帮助信息
#   ./run_n_rule.sh --date 2026-05-14 --zt-date 2026-05-13  # 指定目标日期和涨停日期
#
# 目标日期说明:
#   目标日期 = 涨停后的第一个交易日 (例如: 5月13日涨停, 目标日期为5月14日)
#   如果需要指定涨停日期而非目标日期, 使用: ./run_n_rule.sh --date 目标日期 --zt-date 涨停日期
#

set -e

# 显示帮助信息
show_help() {
    cat << EOF
N规则筛选脚本 - 本地执行优化版

用法:
  ./run_n_rule.sh [日期] [选项]

参数:
  日期          指定目标交易日期, 格式 YYYY-MM-DD
                如果不指定, 默认使用今天日期

选项:
  --help        显示此帮助信息
  --date        指定目标交易日期 (等同于直接传入日期参数)
  --zt-date     指定涨停日期 (前一交易日), 格式 YYYY-MM-DD
                如果不指定, 自动计算为目标日期的前一交易日

示例:
  ./run_n_rule.sh                  # 使用今天日期执行
  ./run_n_rule.sh 2026-05-14       # 执行5月14日的N规则(涨停日为5月13日)
  ./run_n_rule.sh --date 2026-05-14 --zt-date 2026-05-13  # 指定目标日期和涨停日期

说明:
  N规则筛选流程:
  1. 获取前一交易日(涨停日)的涨停股票数据
  2. 批量获取涨停股票的日线数据(45天)
  3. 过滤目标日未涨停/跌停的股票
  4. 应用规则过滤:
     - 规则4: 涨停前7个交易日无跌停、无连续涨停
     - 规则5: 涨停前30个交易日内有涨停记录
  5. 存入 stock_n 表

日志文件:
  执行日志保存在 backend/log/{目标日期}.log
EOF
}

# 解析参数
TARGET_DATE=""
ZT_DATE=""

# 检查是否有 --help 参数
for arg in "$@"; do
    if [ "$arg" = "--help" ]; then
        show_help
        exit 0
    fi
done

# 解析位置参数和选项
while [[ $# -gt 0 ]]; do
    case "$1" in
        --date)
            TARGET_DATE="$2"
            shift 2
            ;;
        --zt-date)
            ZT_DATE="$2"
            shift 2
            ;;
        *)
            # 如果没有设置过日期,且参数看起来像日期格式,则作为目标日期
            if [ -z "$TARGET_DATE" ] && [[ "$1" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
                TARGET_DATE="$1"
            fi
            shift
            ;;
    esac
done

# 构建Python脚本参数
PYTHON_ARGS=""
if [ -n "$TARGET_DATE" ]; then
    PYTHON_ARGS="$PYTHON_ARGS --date $TARGET_DATE"
fi
if [ -n "$ZT_DATE" ]; then
    PYTHON_ARGS="$PYTHON_ARGS --zt-date $ZT_DATE"
fi

# 进入backend目录并执行
cd "$(dirname "$0")/backend"

# 检查是否存在虚拟环境
if [ ! -d ".venv" ] && [ ! -f "pyproject.toml" ]; then
    echo "错误: 未找到Python虚拟环境或项目配置"
    echo "请确保已在 backend 目录初始化项目: uv init"
    exit 1
fi

# 执行筛选脚本
echo "========================================"
echo "开始执行N规则筛选"
echo "目标日期: ${TARGET_DATE:-今天}"
if [ -n "$ZT_DATE" ]; then
    echo "涨停日期: $ZT_DATE"
fi
echo "========================================"

uv run python scripts/filter_stock_n.py $PYTHON_ARGS

EXIT_CODE=$?

echo "========================================"
echo "执行完成 (退出码: $EXIT_CODE)"
echo "日志文件: backend/log/${TARGET_DATE:-$(date +%Y-%m-%d)}.log"
echo "========================================"

exit $EXIT_CODE

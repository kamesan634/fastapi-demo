"""
編號服務

提供編號生成相關功能。
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.kamesan.models.settings import (
    DateFormat,
    DocumentType,
    NumberingRule,
    NumberingSequence,
    ResetPeriod,
)


class NumberingService:
    """編號服務"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _get_period_key(
        self, date_format: DateFormat, reset_period: ResetPeriod
    ) -> str:
        """取得週期鍵值"""
        now = datetime.now(timezone.utc)

        if reset_period == ResetPeriod.NEVER:
            return "GLOBAL"

        if date_format == DateFormat.NONE:
            if reset_period == ResetPeriod.DAILY:
                return now.strftime("%Y%m%d")
            elif reset_period == ResetPeriod.MONTHLY:
                return now.strftime("%Y%m")
            elif reset_period == ResetPeriod.YEARLY:
                return now.strftime("%Y")
            return "GLOBAL"

        if date_format == DateFormat.YYYYMMDD:
            return now.strftime("%Y%m%d")
        elif date_format == DateFormat.YYYYMM:
            return now.strftime("%Y%m")
        elif date_format == DateFormat.YYYY:
            return now.strftime("%Y")

        return "GLOBAL"

    def _get_date_part(self, date_format: DateFormat) -> str:
        """取得日期部分"""
        now = datetime.now(timezone.utc)

        if date_format == DateFormat.YYYYMMDD:
            return now.strftime("%Y%m%d")
        elif date_format == DateFormat.YYYYMM:
            return now.strftime("%Y%m")
        elif date_format == DateFormat.YYYY:
            return now.strftime("%Y")

        return ""

    async def get_rule(
        self, document_type: DocumentType
    ) -> Optional[NumberingRule]:
        """取得編號規則"""
        statement = select(NumberingRule).where(
            NumberingRule.document_type == document_type,
            NumberingRule.is_active == True,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def generate_number(
        self, document_type: DocumentType, commit: bool = True
    ) -> str:
        """
        生成編號

        參數：
            document_type: 單據類型
            commit: 是否提交事務

        回傳值：
            生成的編號

        例外：
            ValueError: 找不到編號規則
        """
        # 取得編號規則
        rule = await self.get_rule(document_type)

        if rule is None:
            # 使用預設規則
            return self._generate_default_number(document_type)

        # 取得週期鍵值
        period_key = self._get_period_key(rule.date_format, rule.reset_period)

        # 取得或建立流水號記錄
        statement = select(NumberingSequence).where(
            NumberingSequence.document_type == document_type,
            NumberingSequence.period_key == period_key,
        )
        result = await self.session.execute(statement)
        sequence = result.scalar_one_or_none()

        if sequence is None:
            sequence = NumberingSequence(
                document_type=document_type,
                period_key=period_key,
                current_sequence=0,
            )
            self.session.add(sequence)
            await self.session.flush()

        # 遞增流水號
        sequence.current_sequence += 1
        self.session.add(sequence)

        if commit:
            await self.session.commit()
        else:
            await self.session.flush()

        # 組合編號
        date_part = self._get_date_part(rule.date_format)
        sequence_part = str(sequence.current_sequence).zfill(rule.sequence_digits)

        return f"{rule.prefix}{date_part}{sequence_part}"

    def _generate_default_number(self, document_type: DocumentType) -> str:
        """生成預設編號（不使用規則時）"""
        import uuid

        now = datetime.now(timezone.utc)
        prefix_map = {
            DocumentType.SALES_ORDER: "ORD",
            DocumentType.PURCHASE_ORDER: "PO",
            DocumentType.GOODS_RECEIPT: "GR",
            DocumentType.SALES_RETURN: "RTN",
            DocumentType.PURCHASE_RETURN: "PR",
            DocumentType.STOCK_COUNT: "SC",
            DocumentType.STOCK_TRANSFER: "ST",
        }
        prefix = prefix_map.get(document_type, "DOC")
        return f"{prefix}{now.strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"

    async def preview_next_number(
        self, document_type: DocumentType
    ) -> tuple[str, str]:
        """
        預覽下一個編號（不實際遞增）

        回傳值：
            (範例編號, 下一個編號)
        """
        rule = await self.get_rule(document_type)

        if rule is None:
            sample = self._generate_default_number(document_type)
            return (sample, sample)

        # 取得週期鍵值
        period_key = self._get_period_key(rule.date_format, rule.reset_period)

        # 查詢當前流水號
        statement = select(NumberingSequence).where(
            NumberingSequence.document_type == document_type,
            NumberingSequence.period_key == period_key,
        )
        result = await self.session.execute(statement)
        sequence = result.scalar_one_or_none()

        current = sequence.current_sequence if sequence else 0
        next_seq = current + 1

        # 組合編號
        date_part = self._get_date_part(rule.date_format)
        sample_seq = str(1).zfill(rule.sequence_digits)
        next_seq_str = str(next_seq).zfill(rule.sequence_digits)

        sample_number = f"{rule.prefix}{date_part}{sample_seq}"
        next_number = f"{rule.prefix}{date_part}{next_seq_str}"

        return (sample_number, next_number)

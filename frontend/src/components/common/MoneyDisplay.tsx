const CURRENCY_SYMBOLS: Record<string, string> = {
  INR: '₹',
  USD: '$',
  GBP: '£',
  EUR: '€',
  JPY: '¥',
};

const SMALLEST_UNIT: Record<string, number> = {
  INR: 100,
  USD: 100,
  GBP: 100,
  EUR: 100,
  JPY: 1,
};

interface Props {
  amount: number;
  currency: string;
}

export default function MoneyDisplay({ amount, currency }: Props) {
  const symbol = CURRENCY_SYMBOLS[currency] ?? currency;
  const divisor = SMALLEST_UNIT[currency] ?? 100;
  const formatted = (amount / divisor).toFixed(2);
  return <span>{symbol}{formatted}</span>;
}

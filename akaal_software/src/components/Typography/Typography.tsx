import type { FC, ReactNode } from 'react';
import styles from './Typography.module.css';

export type TypographyVariant = 'heading' | 'body' | 'caption';
export type TypographySize = 'welcomeSub' | 'welcomeTitle' | 'body' | 'caption' | 'inherit';
export type TypographyWeight = 'regular' | 'medium' | 'semibold' | 'bold';
export type TypographyColor = 'primary' | 'secondary' | 'tertiary' | 'brandEmphasis';
export type TypographyAlign = 'left' | 'center' | 'right';
export type TypographyElement = 'h1' | 'h2' | 'h3' | 'h4' | 'p' | 'span' | 'div';

export interface TypographyProps {
  variant?: TypographyVariant;
  as?: TypographyElement;
  size?: TypographySize;
  weight?: TypographyWeight;
  color?: TypographyColor;
  align?: TypographyAlign;
  className?: string;
  children: ReactNode;
}

export const Typography: FC<TypographyProps> = ({
  variant = 'body',
  as,
  size,
  weight,
  color,
  align = 'left',
  className = '',
  children,
}) => {
  const Component: TypographyElement = as || (variant === 'heading' ? 'h2' : variant === 'caption' ? 'span' : 'p');

  const classNames = [
    styles.typography,
    styles[variant],
    size && styles[`size${capitalize(size)}`],
    weight && styles[`weight${capitalize(weight)}`],
    color && styles[`color${capitalize(color)}`],
    align && styles[`align${capitalize(align)}`],
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return <Component className={classNames}>{children}</Component>;
};

function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/* Helper Compound Components */

export interface HeadingProps extends Omit<TypographyProps, 'variant'> {
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'div';
}

export const Heading: FC<HeadingProps> = ({ as = 'h2', weight = 'semibold', ...props }) => (
  <Typography variant="heading" as={as} weight={weight} {...props} />
);

export interface BodyProps extends Omit<TypographyProps, 'variant'> {}

export const Body: FC<BodyProps> = ({ as = 'p', weight = 'regular', ...props }) => (
  <Typography variant="body" as={as} weight={weight} {...props} />
);

export interface CaptionProps extends Omit<TypographyProps, 'variant'> {}

export const Caption: FC<CaptionProps> = ({ as = 'span', weight = 'regular', ...props }) => (
  <Typography variant="caption" as={as} weight={weight} {...props} />
);

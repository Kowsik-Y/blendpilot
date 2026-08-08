"use client";

import * as React from "react";

/** Calls a callback after a value changes, with its previous value. */
export function useOnChange<T>(value: T, onChange: (current: T, previous: T | undefined) => void) {
  const callbackRef = React.useRef(onChange);
  const previousRef = React.useRef<T | undefined>(undefined);

  React.useEffect(() => {
    callbackRef.current = onChange;
  }, [onChange]);

  React.useEffect(() => {
    const previous = previousRef.current;
    if (!Object.is(value, previous)) {
      callbackRef.current(value, previous);
      previousRef.current = value;
    }
  }, [value]);
}

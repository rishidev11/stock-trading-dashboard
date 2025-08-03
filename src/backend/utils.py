def slidingWindow(prices, windowSize, x_values, y_values):
    i = 0
    while (i+3) < len(prices):
        x_values.append(prices[i:i + windowSize])  # actual values
        y_values.append(prices[i + windowSize])  # actual next-day price
        i += 1

    return x_values, y_values


from utils.imports import *
from utils.data_handler import load_data
from utils.logger import logger


def build_transition_matrix(states_series, n_states=5):
    if states_series.empty or len(states_series) < 2:
        return np.full((n_states, n_states), np.nan)
    matrix = np.zeros((n_states, n_states))
    for i, j in zip(states_series[:-1], states_series[1:]):
        if pd.notna(i) and pd.notna(j):
            i_int, j_int = int(i), int(j)
            if 0 <= i_int < n_states and 0 <= j_int < n_states:
                matrix[i_int][j_int] += 1

    row_sums = matrix.sum(axis=1, keepdims=True)
    return np.divide(
        matrix, row_sums, out=np.full_like(matrix, np.nan), where=(row_sums != 0)
    )


def compute_steady_state(trans_matrix, iterations=200):
    """Compute the steady state by matrix power iteration, ensuring matrix is stochastic."""
    P_work = trans_matrix.copy()
    n_states = P_work.shape[0]

    if n_states == 0:
        print("Warning: Transition matrix is empty. Cannot compute steady state.")
        return np.array([])

    all_nan_rows_original = np.all(np.isnan(P_work), axis=1)

    P_work = np.nan_to_num(P_work, nan=0.0)

    for i in range(n_states):
        if all_nan_rows_original[i]:
            P_work[i, :] = 0.0
            P_work[i, i] = 1.0
        else:
            row_sum = np.sum(P_work[i, :])
            if row_sum > 1e-9:  # If row is not effectively all zeros
                P_work[i, :] /= row_sum
            else:
                P_work[i, :] = 0.0
                P_work[i, i] = 1.0

    try:
        P_final = np.linalg.matrix_power(P_work, iterations)
    except np.linalg.LinAlgError as e:
        print(f"Error during matrix_power: {e}. Returning NaN steady state.")
        return np.full(n_states, np.nan)

    steady_state_vector = P_final[0, :]

    if not (
        np.isclose(np.sum(steady_state_vector), 1.0)
        and np.all(steady_state_vector >= -1e-9)
    ):
        print(
            f"Warning: Steady-state vector from P_final[0,:] (sum={np.sum(steady_state_vector)}) is problematic. Checking other rows or returning NaN."
        )
        for r_idx in range(1, n_states):
            row_vec = P_final[r_idx, :]
            if np.isclose(np.sum(row_vec), 1.0) and np.all(row_vec >= -1e-9):
                print(f"Using row {r_idx} from P_final for steady state.")
                return np.maximum(0, row_vec)

        print("Could not find a valid steady-state vector in P_final rows.")
        return np.full(n_states, np.nan)

    return np.maximum(0, steady_state_vector)


def create_states(prices, n_states=5):
    if prices.empty or len(prices) < 2:
        return pd.Series(dtype=int)
    percent_change = prices.pct_change().dropna()
    if percent_change.empty:
        return pd.Series(dtype=int)
    percent_change_values = percent_change.values
    try:
        if len(np.unique(percent_change_values)) >= n_states:
            states_cat = pd.qcut(
                percent_change_values, q=n_states, labels=False, duplicates="drop"
            )
        else:
            states_cat = pd.cut(
                percent_change_values,
                bins=n_states,
                labels=False,
                retbins=False,
                duplicates="drop",
            )
    except ValueError:
        print(
            f"Warning: Could not discretize states using cut or qcut for {n_states} states. Trying with fewer bins if possible or failing."
        )
        try:
            num_unique_pct = len(np.unique(percent_change_values))
            bins_to_try = min(n_states, num_unique_pct) if num_unique_pct > 0 else 1
            if bins_to_try < 1:
                bins_to_try = 1

            if bins_to_try == 1 and num_unique_pct > 0:
                states_cat = np.zeros(len(percent_change_values), dtype=int)
            elif bins_to_try > 1:
                states_cat = pd.cut(
                    percent_change_values,
                    bins=bins_to_try,
                    labels=False,
                    retbins=False,
                    duplicates="drop",
                )

            else:
                print("Warning: No price variation to create states.")
                return pd.Series(dtype=int)
        except Exception as e_fallback:
            print(f"ERROR: Fallback state creation failed: {e_fallback}")
            return pd.Series(dtype=int)

    if isinstance(states_cat, pd.Series):
        states_cat = states_cat.values  # Ensure numpy array

    valid_states = states_cat[~np.isnan(states_cat) & (states_cat >= 0)].astype(int)
    valid_indices = percent_change.index[~np.isnan(states_cat) & (states_cat >= 0)]

    return pd.Series(valid_states, index=valid_indices)


def run_algorithm(data, csv_file_name):
    logger.debug("Debug: Starting  Markov_chains : run_algorithm")
    logger.debug(data)
    start_date_str = data["startDate"]
    end_date_str = data["endDate"]
    state_labels = ["Big Drop", "Small Drop", "Neutral", "Small Rise", "Big Rise"]
    n_markov_states = len(state_labels)

    data = load_data(csv_file_name)
    if data is None or data.empty:
        print("Failed to load data or data is empty. Exiting.")
        exit()
    if start_date_str:
        data = data[data.index >= pd.to_datetime(start_date_str)]
    if end_date_str:
        data = data[data.index <= pd.to_datetime(end_date_str)]
    if data.empty:
        print("DataFrame became empty after date filtering. Exiting.")
        exit()

    prices = data["Close"]
    if len(prices) < 2:
        print(
            f"Not enough price data points ({len(prices)}) after filtering. Need at least 3 for one transition. Exiting."
        )
        exit()

    states_series = create_states(prices, n_states=n_markov_states)
    if states_series.empty or len(states_series) < 2:
        print(
            "Could not create states or not enough states in sequence for transition matrix. Exiting."
        )
        exit()

    trans_matrix = build_transition_matrix(states_series, n_states=n_markov_states)
    if np.all(np.isnan(trans_matrix)):
        print("Failed to build a valid transition matrix (all NaN). Exiting.")
        exit()

    current_state_idx = states_series.iloc[-1]
    if not (0 <= current_state_idx < len(state_labels)):
        print(
            f"Error: Current state index {current_state_idx} is out of bounds for state_labels (len {len(state_labels)})."
        )
        exit()
    current_state_label = state_labels[current_state_idx]
    current_date = states_series.index[-1].strftime("%Y-%m-%d")

    current_price = prices.loc[states_series.index[-1]]

    if len(states_series.index) >= 2:
        prev_state_date = states_series.index[-2]
        if prev_state_date in prices.index and states_series.index[-1] in prices.index:
            price_today = prices.loc[states_series.index[-1]]
            price_yesterday = prices.loc[prev_state_date]
            if price_yesterday != 0:
                price_change_pct = (
                    (price_today - price_yesterday) / price_yesterday * 100
                )
            else:
                price_change_pct = np.nan
        else:
            price_change_pct = np.nan
    else:
        price_change_pct = np.nan

    print(f"\nCurrent Market State (as of {current_date}):")
    print(f"- Price: ${current_price:.2f}")
    if not np.isnan(price_change_pct):
        print(f"- Daily Change leading to this state: {price_change_pct:+.2f}%")
    else:
        print("- Daily Change leading to this state: N/A")
    print(f"- State: {current_state_label} (Index: {current_state_idx})")

    print("\nTransition Matrix (Probabilities for Next State):")
    trans_matrix_df = pd.DataFrame(
        trans_matrix,
        index=state_labels[:n_markov_states],  # Ensure labels match matrix dim
        columns=[f"Next {s}" for s in state_labels[:n_markov_states]],
    )
    print(trans_matrix_df.round(4).to_string())

    print(f"\nNext State Probabilities (Given Current = {current_state_label}):")
    if 0 <= current_state_idx < trans_matrix.shape[0]:
        current_probs = trans_matrix[current_state_idx]
        if np.all(np.isnan(current_probs)):
            print(
                f"- Probabilities from state {current_state_label} are undefined (state likely not visited as origin, or no outgoing transitions observed)."
            )
        else:
            for state_lbl, prob in zip(state_labels[:n_markov_states], current_probs):
                if pd.notna(prob):
                    print(f"- {state_lbl:<12}: {prob:.2%}")
                else:
                    print(f"- {state_lbl:<12}: N/A")
    else:
        print(
            f"- Current state index {current_state_idx} is out of bounds for the transition matrix."
        )

    if not np.all(np.isnan(trans_matrix)):
        steady_state_probs = compute_steady_state(trans_matrix.copy())
        if steady_state_probs.size > 0 and not np.all(np.isnan(steady_state_probs)):
            print("\nLong-term Market State Distribution (Steady State):")
            for state_lbl, prob in zip(
                state_labels[:n_markov_states], steady_state_probs
            ):
                if pd.notna(prob):
                    print(f"- {state_lbl:<12}: {prob:.2%}")
                else:
                    print(f"- {state_lbl:<12}: N/A")
        else:
            print("\nCould not compute a valid steady-state distribution.")
    else:
        print("\nSkipping steady-state calculation due to invalid transition matrix.")

    print("\n--- Analysis Complete ---")

    if not np.all(np.isnan(trans_matrix)) and state_labels:
        plot_transition_matrix(trans_matrix, state_labels[:n_markov_states])
    else:
        print("Skipping plot: Transition matrix or labels are not available/valid.")

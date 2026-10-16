import numpy as np


class SimplexSolver:
    def __init__(
        self,
        obj_coefficients: list[float],
        constraint_matrix: list[list[float]],
        rhs_values: list[float],
        maximize: bool = True,
        inequalities: list[str] | None = None,
    ) -> None:
        self._maximize: bool = maximize
        original_A: np.ndarray = np.array(constraint_matrix, dtype=float)
        self._b: np.ndarray = np.array(rhs_values, dtype=float)

        # When minimizing, we maximize negative z
        if maximize:
            original_c: np.ndarray = np.array(obj_coefficients, dtype=float)
        else:
            original_c = np.array(obj_coefficients, dtype=float) * -1.0

        self._num_constraints: int = int(original_A.shape[0])
        self._num_vars: int = int(original_A.shape[1])

        # Default to <= if none are provided
        ineq_list: list[str] = (
            list(inequalities) if inequalities else ["<="] * self._num_constraints
        )

        # 1. Standard Form Prep: Ensure RHS is positive
        for i in range(self._num_constraints):
            if self._b[i] < 0:
                self._b[i] *= -1.0
                original_A[i] *= -1.0
                ineq_list[i] = ">=" if ineq_list[i] == "<=" else "<="

        # 2. Big-M Method Setup
        M: float = 1e6  # Large penalty for artificial variables
        extra_A_cols: list[np.ndarray] = []
        extra_c_vals: list[float] = []
        self.basic_indices: list[int] = []
        self.artificial_indices: list[int] = []

        current_var_idx: int = self._num_vars

        for i in range(self._num_constraints):
            ineq: str = ineq_list[i]

            if ineq == "<=":
                # Add Slack Variable
                col: np.ndarray = np.zeros(self._num_constraints)
                col[i] = 1.0
                extra_A_cols.append(col)
                extra_c_vals.append(0.0)
                self.basic_indices.append(current_var_idx)
                current_var_idx += 1

            elif ineq == ">=":
                # Add Surplus Variable (-1)
                col_surplus: np.ndarray = np.zeros(self._num_constraints)
                col_surplus[i] = -1.0
                extra_A_cols.append(col_surplus)
                extra_c_vals.append(0.0)
                current_var_idx += 1

                # Add Artificial Variable (+1) with heavy penalty
                col_art: np.ndarray = np.zeros(self._num_constraints)
                col_art[i] = 1.0
                extra_A_cols.append(col_art)
                extra_c_vals.append(-M)
                self.basic_indices.append(current_var_idx)
                self.artificial_indices.append(current_var_idx)
                current_var_idx += 1

        # 3. Stack everything together
        if extra_A_cols:
            slack_surplus_art_A: np.ndarray = np.column_stack(extra_A_cols)
            self._A: np.ndarray = np.hstack((original_A, slack_surplus_art_A))
            self._c: np.ndarray = np.concatenate((original_c, np.array(extra_c_vals)))
        else:
            self._A = original_A
            self._c = original_c

        self.B_inv: np.ndarray = np.eye(self._num_constraints, dtype=float)
        self.cB: np.ndarray = self._c[self.basic_indices]
        self.status: str = "Optimal Solution Found"

    def solve(self) -> tuple[np.ndarray, float, str]:
        """Executes Revised Simplex loop and returns (b_star, final_z, status)"""
        max_iterations: int = 100
        iteration: int = 0

        while iteration < max_iterations:
            y_star: np.ndarray = self._find_y_star()
            entering_idx: int = self._find_entering_variable_index(y_star)

            if entering_idx == -1:
                self.status = "Optimal Solution Found"
                break

            A_star: np.ndarray = self.B_inv @ self._A[:, entering_idx]
            b_star: np.ndarray = self.B_inv @ self._b

            leaving_row: int = self._minimum_ratio_test(A_star, b_star)
            if leaving_row == -1:
                self.status = "Unbounded Solution"
                break

            self.B_inv = self._build_new_B_inv(A_star, leaving_row)
            self.basic_indices[leaving_row] = entering_idx
            self.cB[leaving_row] = self._c[entering_idx]
            iteration += 1

        # Final Calculations
        final_b_star: np.ndarray = self.B_inv @ self._b
        final_z: float = float(self.cB @ final_b_star)

        # Big-M Infeasibility Check: If an artificial variable is > 0, no valid solution exists.
        for row_idx, var_idx in enumerate(self.basic_indices):
            if var_idx in self.artificial_indices and final_b_star[row_idx] > 1e-5:
                self.status = "Infeasible (No overlapping region)"
                break

        # Flip the mathematically inverted Z value back to normal for minimization
        if not self._maximize:
            final_z = final_z * -1.0

        return final_b_star, final_z, self.status

    def _find_y_star(self) -> np.ndarray:
        """finds y* (cB*B_inv), we pass our simplex problem in as the parameter (non-static method)"""
        y_star: np.ndarray = np.zeros(self._num_constraints, dtype=float)

        # @ operator does matrix multiplication
        y_star = self.cB @ self.B_inv
        return y_star

    def _find_entering_variable_index(self, y_star: np.ndarray) -> int:
        """finds entering variable using y*[A] - c, or returns -1 if optimal"""
        z_star: np.ndarray = np.zeros(self._num_constraints, dtype=float)
        z_star = (y_star @ self._A) - self._c
        entering_variable_index: int = int(np.argmin(z_star)) #argmin returns the index of the smallest value in the entered array

        if z_star[entering_variable_index] < 0: #if there is a negative number in the z row, it's not optimal yet, and should enter the basis
            self.status = "Entering variable is x"+str(entering_variable_index)
            return entering_variable_index
        else: #otherwise, all variables are positive and the solution is optimal
            self.status = "Optimal solution found"
            return -1


    def _minimum_ratio_test(self, A_star: np.ndarray, b_star: np.ndarray) -> int:
        """calculate A* = S* @ A and b* = S* @ b to find row index of our leaving variable, return -1 if unbounded (all are negative or undefined)"""

        #we have to use a tiny number instead of zero to eliminate problems with floating-point errors
        # wrong: positive_leaving_indices = np.argwhere( ratio_arr > 0).flatten()
        valid_rows = np.argwhere(A_star > 1e-9).flatten()

        # These get calculated outside and entered in here
        # A_star: np.ndarray = (self.B_inv @ self._A), entering_col # slices matrix to only get the column we need for our min. ratio test, ':' selects all rows, and we only want the entering variables column
        #
        # b_star: np.ndarray = self.B_inv @ self._b

        if valid_rows.size == 0:
            self.status = "No leaving variable, problem is considered unbounded"
            return -1

        #we get the ratios of only our positive rows
        ratio_arr = b_star[valid_rows] / A_star[valid_rows]

        #argmin gets the index, min gets the value of the smallest number after the ratio test
        min_valid_value = int(np.argmin(ratio_arr))

        #store the index where the leaving variable is located
        leaving_variable_index: int = int(valid_rows[min_valid_value])

        #leaving_variable_index: int = int( valid_rows[ratio_arr[ratio_arr > 0].argmin()] )  # we can easily divide matrices in this manner, we return the smallest value that isn't negative
        self.status = "Leaving variable index is "+str(leaving_variable_index)
        return leaving_variable_index

    def _build_new_B_inv (self, A_star: np.ndarray, leaving_row_index: int) -> np.ndarray:
        """build eta and E and returns E*B_inv for new B_inv (S*) """
        #previously was using the entering column and not the entire new matrix

        eta: np.ndarray = np.zeros(self._num_constraints, dtype=float)
        for i in range(len(A_star)):
            if i == leaving_row_index:
                eta[i] = 1.0/A_star[leaving_row_index]
            else:
                eta[i] = -1*(A_star[i])/A_star[leaving_row_index]

        E: np.ndarray = np.eye(self._num_constraints, dtype=float) #create an identity matrix in the shape of our constaints
        E[:, leaving_row_index] = eta #[select all rows, select the column that aligns with the row that is leaving] = eta vector

        S_star = E @ self.B_inv

        return S_star #returns S*
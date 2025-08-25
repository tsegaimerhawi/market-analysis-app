import React, { useState } from "react";
import { FaChevronDown, FaChevronRight } from "react-icons/fa";

const SideBar = ({ setActiveComponent }) => {
  const [expandedParent, setExpandedParent] = useState(null);

  const toggleParent = (parentId) => {
    setExpandedParent(expandedParent === parentId ? null : parentId);
  };

  const handleClick = (component) => {
    setActiveComponent(component);
  };

  return (
    <div
      className="bg-light border-right"
      style={{ minHeight: "100vh", width: "250px" }}
    >
      <div className="nav flex-column nav-pills">
        <div className="nav-item">
          <button
            className={`nav-link d-flex justify-content-between align-items-center ${
              expandedParent === "stock-prediction" ? "active" : ""
            }`}
            onClick={() => toggleParent("stock-prediction")}
          >
            <span>Stock Prediction</span>
            {expandedParent === "stock-prediction" ? (
              <FaChevronDown />
            ) : (
              <FaChevronRight />
            )}
          </button>
          {expandedParent === "stock-prediction" && (
            <div className="pl-3">
              <a
                href="#"
                className="nav-link text-dark"
                onClick={() => handleClick("stock-prediction-bayesian")}
              >
                Bayesian Based
              </a>
              <a
                href="#"
                className="nav-link text-dark"
                onClick={() => handleClick("stock-prediction-child2")}
              >
                Child 2
              </a>
            </div>
          )}
        </div>

        <div className="nav-item">
          <button
            className={`nav-link d-flex justify-content-between align-items-center ${
              expandedParent === "parent2" ? "active" : ""
            }`}
            onClick={() => toggleParent("parent2")}
          >
            <span>Parent 2</span>
            {expandedParent === "parent2" ? (
              <FaChevronDown />
            ) : (
              <FaChevronRight />
            )}
          </button>
          {expandedParent === "parent2" && (
            <div className="pl-3">
              <a
                href="#"
                className="nav-link text-dark"
                onClick={() => handleClick("parent2-child1")}
              >
                Child 1
              </a>
              <a
                href="#"
                className="nav-link text-dark"
                onClick={() => handleClick("parent2-child2")}
              >
                Child 2
              </a>
            </div>
          )}
        </div>

        <div className="nav-item">
          <button
            className={`nav-link d-flex justify-content-between align-items-center ${
              expandedParent === "parent3" ? "active" : ""
            }`}
            onClick={() => toggleParent("parent3")}
          >
            <span>Parent 3</span>
            {expandedParent === "parent3" ? (
              <FaChevronDown />
            ) : (
              <FaChevronRight />
            )}
          </button>
          {expandedParent === "parent3" && (
            <div className="pl-3">
              <a
                href="#"
                className="nav-link text-dark"
                onClick={() => handleClick("parent3-child1")}
              >
                Child 1
              </a>
              <a
                href="#"
                className="nav-link text-dark"
                onClick={() => handleClick("parent3-child2")}
              >
                Child 2
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SideBar;

import SideBar from "./SideBar";
import Form from "./Form";
import React, { useState } from "react";

const MainLayout = () => {
  const [activeComponent, setActiveComponent] = useState(null);

  const renderMainContent = () => {
    switch (activeComponent) {
      case "stock-prediction-bayesian":
        return <Form />;
      case "stock-prediction-child2":
        return <div>Parent 1 - Child 2 Component</div>;
      case "parent2-child1":
        return <div>Parent 2 - Child 1 Component</div>;
      case "parent2-child2":
        return <div>Parent 2 - Child 2 Component</div>;
      case "parent3-child1":
        return <div>Parent 3 - Child 1 Component</div>;
      case "parent3-child2":
        return <div>Parent 3 - Child 2 Component</div>;
      default:
        return <div>Please select a link</div>;
    }
  };

  return (
    <div className="d-flex">
      <SideBar setActiveComponent={setActiveComponent} />
      <div className="flex-grow-1">
        <div className="container-fluid p-4">
          <div className="flex-grow-1 p-3">{renderMainContent()}</div>
        </div>
      </div>
    </div>
  );
};

export default MainLayout;
